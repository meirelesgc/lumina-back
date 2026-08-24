from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.features.schemas import ConformityFilter
from lumina.models import AbntConformityResult


async def get_by_id(
    session: AsyncSession, result_id: UUID
) -> Optional[AbntConformityResult]:
    return await session.get(AbntConformityResult, result_id)


async def list_all(
    session: AsyncSession, filters: ConformityFilter
) -> list[AbntConformityResult]:
    query = (
        select(AbntConformityResult)
        .where(AbntConformityResult.deleted_at.is_(None))
        .order_by(AbntConformityResult.created_at.desc())
    )

    if filters.doc_id:
        query = query.where(AbntConformityResult.doc_id == filters.doc_id)

    if filters.status:
        query = query.where(AbntConformityResult.status == filters.status)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return list(result.all())


async def count(
    session: AsyncSession, filters: ConformityFilter
) -> int:
    query = (
        select(func.count())
        .select_from(AbntConformityResult)
        .where(AbntConformityResult.deleted_at.is_(None))
    )

    if filters.doc_id:
        query = query.where(AbntConformityResult.doc_id == filters.doc_id)

    if filters.status:
        query = query.where(AbntConformityResult.status == filters.status)

    result = await session.scalar(query)
    return result or 0


def add(session: AsyncSession, result: AbntConformityResult) -> None:
    session.add(result)
