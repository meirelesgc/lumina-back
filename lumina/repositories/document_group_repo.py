from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lumina.models import DocumentGroup, DocumentGroupItem
from lumina.schemas.document_group import DocumentGroupFilter


async def get_by_id(
    session: AsyncSession, group_id: UUID
) -> Optional[DocumentGroup]:
    stmt = (
        select(DocumentGroup)
        .where(DocumentGroup.id == group_id)
        .options(selectinload(DocumentGroup.items))
    )
    return await session.scalar(stmt)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: UUID = None
) -> Optional[DocumentGroup]:
    stmt = select(DocumentGroup).where(
        DocumentGroup.deleted_at.is_(None), DocumentGroup.name == name
    )
    if exclude_id:
        stmt = stmt.where(DocumentGroup.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(
    session: AsyncSession, filters: DocumentGroupFilter
) -> list[DocumentGroup]:
    query = (
        select(DocumentGroup)
        .where(DocumentGroup.deleted_at.is_(None))
        .order_by(DocumentGroup.created_at.desc())
        .options(selectinload(DocumentGroup.items))
    )

    if filters.q:
        query = query.where(DocumentGroup.name.ilike(f'%{filters.q}%'))

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


async def get_item_by_id(
    session: AsyncSession, item_id: UUID
) -> Optional[DocumentGroupItem]:
    return await session.get(DocumentGroupItem, item_id)


async def get_items_by_group(
    session: AsyncSession, group_id: UUID
) -> list[DocumentGroupItem]:
    stmt = (
        select(DocumentGroupItem)
        .where(
            DocumentGroupItem.group_id == group_id,
            DocumentGroupItem.deleted_at.is_(None),
        )
        .order_by(DocumentGroupItem.created_at.desc())
    )
    result = await session.scalars(stmt)
    return result.all()


def add_group(session: AsyncSession, group: DocumentGroup) -> None:
    session.add(group)


def add_item(session: AsyncSession, item: DocumentGroupItem) -> None:
    session.add(item)
