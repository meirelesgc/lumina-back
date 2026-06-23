from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import ProjectDocument
from iaEditais.repositories import project_document_repo
from iaEditais.repositories import project_repo
from iaEditais.schemas.project_document import (
    ProjectDocumentCreate,
    ProjectDocumentPublic,
    ProjectDocumentUpdate,
)
from iaEditais.services import audit_service


async def create_document(
    session: AsyncSession, user_id: UUID, data: ProjectDocumentCreate
) -> ProjectDocument:
    project = await project_repo.get_by_id(session, data.project_id)
    if not project or project.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found',
        )

    db_doc = ProjectDocument(
        project_id=data.project_id,
        type=data.type,
        name=data.name,
        number=data.number,
        status=data.status or 'PENDING',
        responsible=data.responsible,
        typification_ids=data.typification_ids,
    )
    db_doc.set_creation_audit(user_id)

    project_document_repo.add_document(session, db_doc)

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def get_documents_by_project(
    session: AsyncSession, project_id: UUID
) -> list[ProjectDocument]:
    return await project_document_repo.get_by_project(session, project_id)


async def update_document(
    session: AsyncSession, user_id: UUID, data: ProjectDocumentUpdate
) -> ProjectDocument:
    db_doc = await project_document_repo.get_by_id(session, data.id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if data.name is not None:
        db_doc.name = data.name
    if data.type is not None:
        db_doc.type = data.type
    if data.number is not None:
        db_doc.number = data.number
    if data.status is not None:
        db_doc.status = data.status
    if data.responsible is not None:
        db_doc.responsible = data.responsible
    if data.sent_to_kanban is not None:
        db_doc.sent_to_kanban = data.sent_to_kanban
    if data.typification_ids is not None:
        db_doc.typification_ids = data.typification_ids

    db_doc.set_update_audit(user_id)

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def delete_document(
    session: AsyncSession, user_id: UUID, doc_id: UUID
) -> None:
    db_doc = await project_document_repo.get_by_id(session, doc_id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    db_doc.set_deletion_audit(user_id)
    await session.commit()
