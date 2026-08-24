# Endpoints HTTP da feature "Conformidade com Normas ABNT": disparo/consulta da auditoria ABNT, delegado a lumina/features/abnt_conformity_service.py.

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    UploadFile,
)

from lumina.core.dependencies import CurrentUser, Session
from lumina.features import abnt_conformity_service
from lumina.features.schemas import (
    ConformityFilter,
    ProcessingAccepted,
    ProcessingResult,
    ProcessingResultList,
)

router = APIRouter(prefix='/abnt', tags=['conformidade com abnt'])


@router.get('/results', response_model=ProcessingResultList)
async def list_abnt_compliance_results(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[ConformityFilter, Depends()],
):
    results = await abnt_conformity_service.list_results(session, filters)
    total = await abnt_conformity_service.count_results(session, filters)
    return {'count': total, 'results': results}


@router.get('/results/{result_id}', response_model=ProcessingResult)
async def get_abnt_compliance_result_by_id(
    result_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await abnt_conformity_service.get_result_by_id(
        session, result_id
    )


@router.delete(
    '/results/{result_id}', status_code=HTTPStatus.NO_CONTENT
)
async def delete_abnt_compliance_result(
    result_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await abnt_conformity_service.delete_result(
        session, current_user.id, result_id
    )


@router.post(
    '/{doc_id}/conformidade',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_abnt_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    content = await file.read()
    return await abnt_conformity_service.start_analysis(
        session,
        current_user.id,
        doc_id,
        file.filename,
        content,
        background_tasks,
    )


@router.get('/{doc_id}/conformidade', response_model=ProcessingResultList)
async def get_abnt_result(
    doc_id: str,
    session: Session,
    current_user: CurrentUser,
):
    filters = ConformityFilter(doc_id=doc_id)
    results = await abnt_conformity_service.list_results(session, filters)
    return {'count': len(results), 'results': results}
