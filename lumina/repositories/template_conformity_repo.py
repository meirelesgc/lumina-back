from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.features.schemas import ConformityFilter
from lumina.models import TemplateConformityResult


async def get_by_id(
    session: AsyncSession, result_id: UUID
) -> Optional[TemplateConformityResult]:
    return await session.get(TemplateConformityResult, result_id)


async def list_all(
    session: AsyncSession, filters: ConformityFilter
) -> list[TemplateConformityResult]:
    query = (
        select(TemplateConformityResult)
        .where(TemplateConformityResult.deleted_at.is_(None))
        .order_by(TemplateConformityResult.created_at.desc())
    )

    if filters.doc_id:
        query = query.where(TemplateConformityResult.doc_id == filters.doc_id)

    if filters.status:
        query = query.where(TemplateConformityResult.status == filters.status)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return list(result.all())


async def count(
    session: AsyncSession, filters: ConformityFilter
) -> int:
    query = (
        select(func.count())
        .select_from(TemplateConformityResult)
        .where(TemplateConformityResult.deleted_at.is_(None))
    )

    if filters.doc_id:
        query = query.where(TemplateConformityResult.doc_id == filters.doc_id)

    if filters.status:
        query = query.where(TemplateConformityResult.status == filters.status)

    result = await session.scalar(query)
    return result or 0


def add(session: AsyncSession, result: TemplateConformityResult) -> None:
    session.add(result)
