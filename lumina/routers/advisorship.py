from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from lumina.core.dependencies import CurrentUser, Session
from lumina.schemas.advisorship import (
    AdviseeListPublic,
    AdvisorListPublic,
    AdvisorshipCreate,
    AdvisorshipFilter,
    AdvisorshipList,
    AdvisorshipPublic,
    AdvisorshipUpdate,
    DocumentAcademicContextPublic,
)
from lumina.schemas.common import Message
from lumina.schemas.document import DocumentList
from lumina.services import advisorship_service

router = APIRouter(
    prefix='/advisorship',
    tags=['orientação, orientadores e orientandos'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=AdvisorshipPublic,
    summary='Criar vínculo de orientação',
    description='Cria uma relação N-N de orientação/supervisão.',
)
async def create_advisorship(
    data: AdvisorshipCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await advisorship_service.create_advisorship(
        session, current_user, data
    )


@router.get(
    '',
    response_model=AdvisorshipList,
    summary='Listar vínculos de orientação',
    description='Lista relacionamentos de orientação com suporte a filtros.',
)
async def list_advisorships(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[AdvisorshipFilter, Depends()],
):
    items = await advisorship_service.list_advisorships(
        session, current_user, filters
    )
    return {'advisorships': items}


@router.get(
    '/my-advisees',
    response_model=AdviseeListPublic,
    summary='Listar meus orientandos (Visão do Orientador)',
    description='Retorna todos os pesquisadores orientados pelo usuário.',
)
async def get_my_advisees(
    session: Session,
    current_user: CurrentUser,
    status: Optional[str] = None,
):
    advisees = await advisorship_service.get_my_advisees(
        session, current_user, status=status
    )
    return {'advisees': advisees}


@router.get(
    '/advisees/{advisee_id}/documents',
    response_model=DocumentList,
    summary='Listar documentos do orientando',
    description='Retorna documentos submetidos pelo orientando.',
)
async def get_advisee_documents(
    advisee_id: UUID,
    session: Session,
    current_user: CurrentUser,
    project_id: Optional[UUID] = None,
):
    docs = await advisorship_service.get_advisee_documents(
        session, current_user, advisee_id, project_id=project_id
    )
    return {'documents': docs}


@router.get(
    '/my-advisors',
    response_model=AdvisorListPublic,
    summary='Listar meus orientadores (Visão do Orientando)',
    description='Retorna orientadores vinculados ao usuário logado.',
)
async def get_my_advisors(
    session: Session,
    current_user: CurrentUser,
    status: Optional[str] = None,
):
    advisors = await advisorship_service.get_my_advisors(
        session, current_user, status=status
    )
    return {'advisors': advisors}


@router.get(
    '/documents/{doc_id}/academic-context',
    response_model=DocumentAcademicContextPublic,
    summary='Obter contexto acadêmico do documento',
    description='Retorna autoria (orientando), orientadores e projeto.',
)
async def get_document_academic_context(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await advisorship_service.get_document_academic_context(
        session, current_user, doc_id
    )


@router.get(
    '/{advisorship_id}',
    response_model=AdvisorshipPublic,
    summary='Obter vínculo por ID',
)
async def get_advisorship_by_id(
    advisorship_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await advisorship_service.get_advisorship_by_id(
        session, current_user, advisorship_id
    )


@router.put(
    '/{advisorship_id}',
    response_model=AdvisorshipPublic,
    summary='Atualizar vínculo de orientação',
)
async def update_advisorship(
    advisorship_id: UUID,
    data: AdvisorshipUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await advisorship_service.update_advisorship(
        session, current_user, advisorship_id, data
    )


@router.delete(
    '/{advisorship_id}',
    response_model=Message,
    summary='Remover vínculo de orientação',
)
async def delete_advisorship(
    advisorship_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await advisorship_service.delete_advisorship(
        session, current_user, advisorship_id
    )
    return Message(message='Vínculo de orientação removido com sucesso.')
