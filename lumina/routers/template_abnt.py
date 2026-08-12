from http import HTTPStatus
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from lumina.features.template_abnt import service
from lumina.features.template_abnt.schemas import (
    ProcessingAccepted,
    ProcessingResult,
    TemplatesListResponse,
)

router = APIRouter(
    prefix='/template-abnt',
    tags=['conformidade com template e normas ABNT'],
)


@router.get('/templates', response_model=TemplatesListResponse)
async def list_templates():
    return {'templates': service.list_templates()}


@router.post(
    '/{doc_id}/template',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_template_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    template_name: Annotated[str, Form()] = service.DEFAULT_TEMPLATE_NAME,
    file: UploadFile = File(...),
):
    template_path = service.resolve_template_path(template_name)
    if template_path is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Template não encontrado.',
        )

    content = await file.read()
    article_path = service.save_upload(
        doc_id, file.filename or 'artigo.pdf', content, prefix='template'
    )

    store = service.get_template_store()
    service.mark_processing(store, doc_id)
    background_tasks.add_task(
        service.run_template_analysis, doc_id, template_path, article_path
    )

    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/template', response_model=ProcessingResult)
async def get_template_result(doc_id: str):
    result = service.get_template_store().get(doc_id)
    if result is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Nenhum processamento de template encontrado para este documento.',
        )
    return result


@router.post(
    '/{doc_id}/abnt',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_abnt_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    content = await file.read()
    article_path = service.save_upload(
        doc_id, file.filename or 'artigo.pdf', content, prefix='abnt'
    )

    store = service.get_abnt_store()
    service.mark_processing(store, doc_id)
    background_tasks.add_task(service.run_abnt_analysis, doc_id, article_path)

    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/abnt', response_model=ProcessingResult)
async def get_abnt_result(doc_id: str):
    result = service.get_abnt_store().get(doc_id)
    if result is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Nenhum processamento ABNT encontrado para este documento.',
        )
    return result
