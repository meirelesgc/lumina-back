# Endpoints HTTP da feature "Conformidade com Normas ABNT": disparo/consulta da auditoria ABNT, delegado a lumina/features/abnt_conformity_service.py.

from http import HTTPStatus

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
)

from lumina.core.dependencies import CurrentUser
from lumina.features import abnt_conformity_service
from lumina.features.json_store import JsonResultStore
from lumina.features.schemas import (
    ProcessingAccepted,
    ProcessingResult,
)

router = APIRouter(prefix='/abnt', tags=['conformidade com abnt'])

RESULT_NOT_FOUND_DETAIL = 'Nenhum processamento ABNT encontrado para este documento.'


def get_result_or_404(store: JsonResultStore, doc_id: str) -> dict:
    result = store.get(doc_id)
    if result is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=RESULT_NOT_FOUND_DETAIL)
    return result


@router.post(
    '/{doc_id}/conformidade',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_abnt_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    content = await file.read()
    abnt_conformity_service.start_analysis(doc_id, file.filename, content, background_tasks)
    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/conformidade', response_model=ProcessingResult)
async def get_abnt_result(doc_id: str, current_user: CurrentUser):
    return get_result_or_404(abnt_conformity_service.get_store(), doc_id)
