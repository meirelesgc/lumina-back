# Endpoints HTTP da feature "Conformidade com Template": CRUD dos templates cadastrados (delegado a lumina/services/publication_template_service.py) e disparo/consulta da verificação de conformidade (delegado a lumina/features/template_conformity_service.py).

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from lumina.core.dependencies import CurrentUser, Session, TemplateStorage
from lumina.features import template_conformity_service
from lumina.features.json_store import JsonResultStore
from lumina.features.schemas import (
    ProcessingAccepted,
    ProcessingResult,
)
from lumina.schemas.publication_template import (
    PublicationTemplateFilter,
    PublicationTemplateList,
    PublicationTemplatePublic,
    PublicationTemplateUpdate,
)
from lumina.services import publication_template_service

router = APIRouter(prefix='/templates', tags=['conformidade com template'])

RESULT_NOT_FOUND_DETAIL = 'Nenhum processamento de template encontrado para este documento.'


def get_result_or_404(store: JsonResultStore, doc_id: str) -> dict:
    result = store.get(doc_id)
    if result is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=RESULT_NOT_FOUND_DETAIL)
    return result


@router.get('', response_model=PublicationTemplateList)
async def list_templates(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[PublicationTemplateFilter, Depends()],
):
    templates = await publication_template_service.get_templates(session, filters)
    return {'templates': templates}


@router.post('', status_code=HTTPStatus.CREATED, response_model=PublicationTemplatePublic)
async def create_template(
    session: Session,
    current_user: CurrentUser,
    storage: TemplateStorage,
    name: Annotated[str, Form()],
    file: UploadFile = File(...),
):
    return await publication_template_service.create_template(
        session, current_user.id, storage, name, file
    )


@router.get('/{template_id}', response_model=PublicationTemplatePublic)
async def get_template(
    template_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await publication_template_service.get_template_by_id(session, template_id)


@router.put('/{template_id}', response_model=PublicationTemplatePublic)
async def update_template(
    template_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: TemplateStorage,
    name: Annotated[str | None, Form()] = None,
    file: UploadFile | None = File(None),
):
    data = PublicationTemplateUpdate(id=template_id, name=name)
    return await publication_template_service.update_template(
        session, current_user.id, storage, data, file
    )


@router.delete('/{template_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_template(
    template_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await publication_template_service.delete_template(session, current_user.id, template_id)


@router.post(
    '/{doc_id}/conformidade',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_template_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    session: Session,
    current_user: CurrentUser,
    template_id: Annotated[UUID, Form()],
    file: UploadFile = File(...),
):
    template_path = await publication_template_service.get_template_file_path(
        session, template_id
    )

    content = await file.read()
    template_conformity_service.start_analysis(doc_id, file.filename, content, template_path, background_tasks)
    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/conformidade', response_model=ProcessingResult)
async def get_template_result(doc_id: str, current_user: CurrentUser):
    return get_result_or_404(template_conformity_service.get_store(), doc_id)
