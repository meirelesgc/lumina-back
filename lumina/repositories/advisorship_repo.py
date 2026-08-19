from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lumina.models import Advisorship, Document, ProjectDocument, User
from lumina.schemas.advisorship import AdvisorshipFilter


async def get_by_id(
    session: AsyncSession, advisorship_id: UUID
) -> Optional[Advisorship]:
    stmt = (
        select(Advisorship)
        .options(
            selectinload(Advisorship.advisor),
            selectinload(Advisorship.advisee),
            selectinload(Advisorship.project),
        )
        .where(
            Advisorship.id == advisorship_id,
            Advisorship.deleted_at.is_(None),
        )
    )
    return await session.scalar(stmt)


async def get_active_pair(
    session: AsyncSession,
    advisor_id: UUID,
    advisee_id: UUID,
    project_id: Optional[UUID] = None,
    role_type: str = 'MAIN_ADVISOR',
) -> Optional[Advisorship]:
    stmt = select(Advisorship).where(
        Advisorship.deleted_at.is_(None),
        Advisorship.advisor_id == advisor_id,
        Advisorship.advisee_id == advisee_id,
        Advisorship.role_type == role_type,
    )
    if project_id:
        stmt = stmt.where(Advisorship.project_id == project_id)
    else:
        stmt = stmt.where(Advisorship.project_id.is_(None))

    return await session.scalar(stmt)


def add_advisorship(session: AsyncSession, advisorship: Advisorship) -> None:
    session.add(advisorship)


async def list_all(
    session: AsyncSession, filters: AdvisorshipFilter
) -> Sequence[Advisorship]:
    stmt = (
        select(Advisorship)
        .options(
            selectinload(Advisorship.advisor),
            selectinload(Advisorship.advisee),
            selectinload(Advisorship.project),
        )
        .where(Advisorship.deleted_at.is_(None))
        .order_by(Advisorship.created_at.desc())
    )

    if filters.advisor_id:
        stmt = stmt.where(Advisorship.advisor_id == filters.advisor_id)
    if filters.advisee_id:
        stmt = stmt.where(Advisorship.advisee_id == filters.advisee_id)
    if filters.project_id:
        stmt = stmt.where(Advisorship.project_id == filters.project_id)
    if filters.role_type:
        stmt = stmt.where(Advisorship.role_type == filters.role_type.value)
    if filters.status:
        stmt = stmt.where(Advisorship.status == filters.status.value)
    if filters.q:
        search = f'%{filters.q}%'
        stmt = stmt.join(Advisorship.advisee).where(
            or_(
                User.username.ilike(search),
                User.email.ilike(search),
                Advisorship.topic.ilike(search),
            )
        )

    stmt = stmt.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(stmt)
    return result.all()


async def list_by_advisor(
    session: AsyncSession,
    advisor_id: UUID,
    status: Optional[str] = None,
) -> Sequence[Advisorship]:
    stmt = (
        select(Advisorship)
        .options(
            selectinload(Advisorship.advisor),
            selectinload(Advisorship.advisee),
            selectinload(Advisorship.project),
        )
        .where(
            Advisorship.advisor_id == advisor_id,
            Advisorship.deleted_at.is_(None),
        )
        .order_by(Advisorship.created_at.desc())
    )
    if status:
        stmt = stmt.where(Advisorship.status == status)

    result = await session.scalars(stmt)
    return result.all()


async def list_by_advisee(
    session: AsyncSession,
    advisee_id: UUID,
    status: Optional[str] = None,
) -> Sequence[Advisorship]:
    stmt = (
        select(Advisorship)
        .options(
            selectinload(Advisorship.advisor),
            selectinload(Advisorship.advisee),
            selectinload(Advisorship.project),
        )
        .where(
            Advisorship.advisee_id == advisee_id,
            Advisorship.deleted_at.is_(None),
        )
        .order_by(Advisorship.created_at.desc())
    )
    if status:
        stmt = stmt.where(Advisorship.status == status)

    result = await session.scalars(stmt)
    return result.all()


async def get_advisee_document_metrics(
    session: AsyncSession,
    advisee_id: UUID,
    project_id: Optional[UUID] = None,
) -> dict[str, int]:
    # Conta documentos onde o advisee é o autor (created_by) ou editor
    query = select(
        func.count(Document.id).label('total'),
        func.count(Document.id)
        .filter(Document.processing_status == 'WAITING_FOR_REVIEW')
        .label('pending'),
    ).where(
        Document.deleted_at.is_(None),
        Document.created_by == advisee_id,
    )

    if project_id:
        # Se filtrado por projeto, junta com ProjectDocument
        query = query.join(
            ProjectDocument,
            Document.project_document_id == ProjectDocument.id,
        ).where(ProjectDocument.project_id == project_id)

    result = await session.execute(query)
    row = result.first()
    if row:
        return {'total': row.total or 0, 'pending': row.pending or 0}
    return {'total': 0, 'pending': 0}


async def get_advisee_documents(
    session: AsyncSession,
    advisee_id: UUID,
    project_id: Optional[UUID] = None,
) -> Sequence[Document]:
    stmt = (
        select(Document)
        .options(
            selectinload(Document.history),
            selectinload(Document.typifications),
            selectinload(Document.editors),
            selectinload(Document.project_document),
        )
        .where(
            Document.deleted_at.is_(None),
            Document.created_by == advisee_id,
        )
        .order_by(Document.created_at.desc())
    )

    if project_id:
        stmt = stmt.join(
            ProjectDocument,
            Document.project_document_id == ProjectDocument.id,
        ).where(ProjectDocument.project_id == project_id)

    result = await session.scalars(stmt)
    return result.all()
