from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import PublicationTemplate
from lumina.schemas.publication_template import PublicationTemplateFilter


async def get_by_id(
    session: AsyncSession, template_id: UUID
) -> Optional[PublicationTemplate]:
    return await session.get(PublicationTemplate, template_id)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: Optional[UUID] = None
) -> Optional[PublicationTemplate]:
    stmt = select(PublicationTemplate).where(
        PublicationTemplate.deleted_at.is_(None),
        PublicationTemplate.name == name,
    )
    if exclude_id:
        stmt = stmt.where(PublicationTemplate.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(
    session: AsyncSession, filters: PublicationTemplateFilter
) -> list[PublicationTemplate]:
    query = (
        select(PublicationTemplate)
        .where(PublicationTemplate.deleted_at.is_(None))
        .order_by(PublicationTemplate.created_at.desc())
    )

    if filters.q:
        query = query.where(PublicationTemplate.name.ilike(f'%{filters.q}%'))

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add(session: AsyncSession, template: PublicationTemplate) -> None:
    session.add(template)
