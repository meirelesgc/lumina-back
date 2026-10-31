from http import HTTPStatus
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.core.storage_provider import UPLOAD_DIRECTORY
from lumina.models import (
    Document,
    DocumentRelease,
    Project,
    ProjectDocument,
    Source,
    User,
    UserImage,
)
from lumina.services import access_service


async def _can_read_file(session: AsyncSession, user: User, url: str) -> bool:
    if access_service.is_admin(user):
        return True

    for model in (UserImage, Source):
        if await session.scalar(
            select(model.id).where(model.file_path == url)
        ):
            return True

    documents = await session.scalars(
        select(Document)
        .join(DocumentRelease, DocumentRelease.document_id == Document.id)
        .where(DocumentRelease.file_path == url)
    )
    for document in documents.all():
        if await access_service.can_read_document(session, user, document):
            return True

    projects = await session.scalars(
        select(Project)
        .join(ProjectDocument, ProjectDocument.project_id == Project.id)
        .where(ProjectDocument.file_path == url)
    )
    for project in projects.all():
        if await access_service.can_read_project(session, user, project):
            return True

    return False


async def get_authorized_path(
    session: AsyncSession, user: User, file_path: str
) -> Path:
    root = Path(UPLOAD_DIRECTORY).resolve()
    path = (root / file_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='File not found'
        )

    if not await _can_read_file(session, user, f'/uploads/{file_path}'):
        raise access_service.forbidden('Acesso negado a este arquivo.')

    return path
