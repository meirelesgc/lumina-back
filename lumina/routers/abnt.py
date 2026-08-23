# Endpoints HTTP da feature "Conformidade com Normas ABNT": disparo/consulta da auditoria ABNT, delegado a lumina/features/abnt_conformity_service.py.

from http import HTTPStatus

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    UploadFile,
)

from lumina.core.dependencies import CurrentUser
from lumina.features import abnt_conformity_service
from lumina.features.schemas import (
    ProcessingAccepted,
    ProcessingResultList,
)

router = APIRouter(prefix='/abnt', tags=['conformidade com abnt'])


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
    return abnt_conformity_service.start_analysis(
        doc_id, file.filename, content, background_tasks
    )


@router.get('/{doc_id}/conformidade', response_model=ProcessingResultList)
async def get_abnt_result(doc_id: str, current_user: CurrentUser):
    return {'results': abnt_conformity_service.list_results(doc_id)}
