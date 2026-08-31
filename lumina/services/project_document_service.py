from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import ProjectDocument, User
from lumina.repositories import project_document_repo
from lumina.schemas.project_document import (
    ProjectDocumentCreate,
    ProjectDocumentUpdate,
)
from lumina.services import project_service


async def create_document(
    session: AsyncSession, current_user: User, data: ProjectDocumentCreate
) -> ProjectDocument:
    await project_service.get_project_by_id(
        session, current_user, data.project_id
    )

    db_doc = ProjectDocument(
        project_id=data.project_id,
        type=data.type,
        name=data.name,
        number=data.number,
        status=data.status or 'PENDING',
        responsible=data.responsible,
        responsibles=[str(uid) for uid in data.responsibles or []],
        typification_ids=data.typification_ids,
    )
    db_doc.set_creation_audit(current_user.id)

    project_document_repo.add_document(session, db_doc)

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def get_documents_by_project(
    session: AsyncSession, current_user: User, project_id: UUID
) -> list[ProjectDocument]:
    await project_service.get_project_by_id(
        session, current_user, project_id
    )
    return await project_document_repo.get_by_project(session, project_id)


async def update_document(
    session: AsyncSession, current_user: User, data: ProjectDocumentUpdate
) -> ProjectDocument:
    db_doc = await project_document_repo.get_by_id(session, data.id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    await project_service.get_project_by_id(
        session, current_user, db_doc.project_id
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
    if data.responsibles is not None:
        db_doc.responsibles = [str(uid) for uid in data.responsibles]
    if data.sent_to_kanban is not None:
        db_doc.sent_to_kanban = data.sent_to_kanban
    if data.typification_ids is not None:
        db_doc.typification_ids = data.typification_ids

    db_doc.set_update_audit(current_user.id)

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def delete_document(
    session: AsyncSession, current_user: User, doc_id: UUID
) -> None:
    db_doc = await project_document_repo.get_by_id(session, doc_id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    await project_service.get_project_by_id(
        session, current_user, db_doc.project_id
    )

    db_doc.set_deletion_audit(current_user.id)
    await session.commit()
