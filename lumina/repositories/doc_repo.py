from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from lumina.models import (
    AccessType,
    Advisorship,
    Document,
    DocumentHistory,
    Typification,
    User,
)
from lumina.repositories import util
from lumina.schemas.document import DocumentFilter, DocumentScope


async def get_by_id(session: AsyncSession, doc_id: UUID) -> Optional[Document]:
    stmt = select(Document).where(Document.id == doc_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_project_document_id(
    session: AsyncSession, project_document_id: UUID
) -> Optional[Document]:
    stmt = select(Document).where(
        Document.project_document_id == project_document_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_identifier(
    session: AsyncSession, identifier: str, exclude_id: UUID = None
) -> Optional[Document]:
    stmt = select(Document).where(
        Document.identifier == identifier,
        Document.deleted_at.is_(None),
    )
    if exclude_id:
        stmt = stmt.where(Document.id != exclude_id)
    return await session.scalar(stmt)


async def has_document_access(
    session: AsyncSession, current_user: User, doc: Document
) -> bool:
    if current_user.access_level == AccessType.ADMIN:
        return True

    if doc.created_by == current_user.id:
        return True

    if any(editor.id == current_user.id for editor in doc.editors):
        return True

    if doc.created_by:
        stmt = select(Advisorship.id).where(
            Advisorship.advisor_id == current_user.id,
            Advisorship.advisee_id == doc.created_by,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )
        if await session.scalar(stmt):
            return True

    if doc.advisorship_id:
        stmt = select(Advisorship.id).where(
            Advisorship.id == doc.advisorship_id,
            Advisorship.advisor_id == current_user.id,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )
        if await session.scalar(stmt):
            return True

    return False


async def list_all(
    session: AsyncSession, current_user: User, filters: DocumentFilter
) -> list[Document]:
    # Lógica de Lateral Join para pegar o último histórico
    last_history_subq = (
        select(DocumentHistory)
        .where(DocumentHistory.document_id == Document.id)
        .order_by(DocumentHistory.created_at.desc())
        .limit(1)
        .lateral()
    )

    last_history = aliased(DocumentHistory, last_history_subq)

    query = (
        select(Document)
        .join(last_history, true())
        .where(Document.deleted_at.is_(None))
        .order_by(last_history.status.asc(), last_history.created_at.asc())
    )

    # Controle de Acesso e Escopo
    is_admin = current_user.access_level == AccessType.ADMIN

    if is_admin:
        if filters.advisee_id:
            query = query.where(Document.created_by == filters.advisee_id)
        elif filters.mine_only or filters.scope == DocumentScope.MINE:
            query = query.where(
                (Document.created_by == current_user.id)
                | (Document.editors.any(User.id == current_user.id))
            )
        # Se is_admin e scope == ALL, vê todos os docs
    else:
        # Usuário comum ou orientador
        advisee_ids_subq = select(Advisorship.advisee_id).where(
            Advisorship.advisor_id == current_user.id,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )
        advisorship_ids_subq = select(Advisorship.id).where(
            Advisorship.advisor_id == current_user.id,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )

        if filters.advisee_id:
            # Filtra por orientando específico
            query = query.where(
                Document.created_by == filters.advisee_id,
                Document.created_by.in_(advisee_ids_subq),
            )
        elif filters.scope == DocumentScope.ADVISEES:
            # Documentos dos orientandos ativos
            query = query.where(
                (Document.created_by.in_(advisee_ids_subq))
                | (Document.advisorship_id.in_(advisorship_ids_subq))
            )
        elif filters.scope == DocumentScope.ALL:
            # Meus documentos + Documentos dos meus orientandos
            query = query.where(
                (Document.created_by == current_user.id)
                | (Document.editors.any(User.id == current_user.id))
                | (Document.created_by.in_(advisee_ids_subq))
                | (Document.advisorship_id.in_(advisorship_ids_subq))
            )
        else:
            # Padrão: MINE (meus documentos criados + onde sou editor)
            query = query.where(
                (Document.created_by == current_user.id)
                | (Document.editors.any(User.id == current_user.id))
            )

    if filters.archived is not None:
        query = query.where(Document.is_archived == filters.archived)

    if filters.q:
        query = util.apply_text_search(query, Document, filters.q)

    if filters.source:
        query = query.where(Document.source == filters.source)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    return result.all()


async def get_typifications_by_ids(
    session: AsyncSession, ids: list[UUID]
) -> Sequence[Typification]:
    if not ids:
        return []
    stmt = select(Typification).where(Typification.id.in_(ids))
    result = await session.scalars(stmt)
    return result.all()


async def get_users_by_ids(
    session: AsyncSession, ids: list[UUID]
) -> Sequence[User]:
    if not ids:
        return []
    stmt = select(User).where(User.id.in_(ids))
    result = await session.scalars(stmt)
    return result.all()


def add_document(session: AsyncSession, doc: Document) -> None:
    session.add(doc)


def add_history(session: AsyncSession, history: DocumentHistory) -> None:
    session.add(history)
