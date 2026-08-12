from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from lumina.core.dependencies import CurrentUser, Session
from lumina.schemas import (
    DocumentCreate,
    DocumentFilter,
    DocumentList,
    DocumentPublic,
    DocumentUpdate,
)
from lumina.services import doc_service

router = APIRouter(prefix='/doc', tags=['verificação dos documentos, editais'])


@router.post('', status_code=HTTPStatus.CREATED, response_model=DocumentPublic)
async def create_doc(
    doc: DocumentCreate, session: Session, current_user: CurrentUser
):
    return await doc_service.create_doc(session, current_user, doc)


@router.get('', response_model=DocumentList)
async def read_docs(
    session: Session, filters: Annotated[DocumentFilter, Depends()]
):
    docs = await doc_service.get_docs(session, filters)
    return {'documents': docs}


@router.get(
    '/by-project-document/{project_document_id}', response_model=DocumentPublic
)
async def read_doc_by_project_document(
    project_document_id: UUID, session: Session
):
    return await doc_service.get_doc_by_project_document_id(
        session, project_document_id
    )


@router.get('/{doc_id}', response_model=DocumentPublic)
async def read_doc(doc_id: UUID, session: Session):
    return await doc_service.get_doc_by_id(session, doc_id)


@router.get('/{doc_id}/context-items')
async def read_doc_context_items(doc_id: UUID, session: Session):
    items = await doc_service.get_doc_context_items(session, doc_id)
    return {'items': items}


@router.put('', response_model=DocumentPublic)
async def update_doc(
    doc: DocumentUpdate, session: Session, current_user: CurrentUser
):
    return await doc_service.update_doc(session, current_user, doc)


@router.put('/{document_id}/toggle-archive', response_model=DocumentPublic)
async def toggle_archive(
    document_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await doc_service.toggle_archive(session, current_user, document_id)


@router.delete(
    '/{doc_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_doc(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    await doc_service.delete_doc(session, current_user, doc_id)
    return {'message': 'Doc deleted successfully'}
