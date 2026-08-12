from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter

from lumina.core.dependencies import CurrentUser, Session
from lumina.schemas.project_document import (
    ProjectDocumentCreate,
    ProjectDocumentList,
    ProjectDocumentPublic,
    ProjectDocumentUpdate,
)
from lumina.services import project_document_service

router = APIRouter(
    prefix='/project-document',
    tags=['projetos, documentos'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=ProjectDocumentPublic,
    summary='Criar documento de projeto',
    description='Adiciona um novo documento a um projeto, com responsável, status e controle de envio ao kanban.',
)
async def create_document(
    document: ProjectDocumentCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await project_document_service.create_document(
        session, current_user.id, document
    )


@router.get(
    '/by-project/{project_id}',
    response_model=ProjectDocumentList,
    summary='Listar documentos de um projeto',
    description='Retorna todos os documentos associados a um projeto específico.',
)
async def read_documents_by_project(project_id: UUID, session: Session):
    documents = await project_document_service.get_documents_by_project(
        session, project_id
    )
    return {'documents': documents}


@router.put(
    '',
    response_model=ProjectDocumentPublic,
    summary='Atualizar documento de projeto',
    description='Atualiza os dados de um documento de projeto (nome, responsável, status, envio ao kanban).',
)
async def update_document(
    document: ProjectDocumentUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await project_document_service.update_document(
        session, current_user.id, document
    )


@router.delete(
    '/{doc_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir documento de projeto',
    description='Remove (soft-delete) um documento de projeto.',
)
async def delete_document(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await project_document_service.delete_document(
        session, current_user.id, doc_id
    )
    return {'message': 'Document deleted'}
