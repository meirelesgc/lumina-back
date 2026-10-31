from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import AccessType, Document, Project, User
from lumina.repositories import doc_repo, project_repo


def is_admin(user: User) -> bool:
    return user.access_level == AccessType.ADMIN


def forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=detail)


def ensure_admin(user: User) -> None:
    if not is_admin(user):
        raise forbidden('Acesso restrito a administradores.')


def ensure_owner_or_admin(
    user: User, owner_id, detail: str = 'Acesso negado.'
) -> None:
    if user.id != owner_id and not is_admin(user):
        raise forbidden(detail)


async def can_read_document(
    session: AsyncSession, user: User, doc: Document
) -> bool:
    return is_admin(user) or await doc_repo.has_document_access(
        session, user, doc
    )


def can_edit_document(user: User, doc: Document) -> bool:
    return (
        is_admin(user)
        or doc.created_by == user.id
        or any(editor.id == user.id for editor in doc.editors)
    )


def can_delete_document(user: User, doc: Document) -> bool:
    return is_admin(user) or doc.created_by == user.id


async def can_read_project(
    session: AsyncSession, user: User, project: Project
) -> bool:
    return is_admin(user) or await project_repo.has_project_access(
        session, user, project
    )
