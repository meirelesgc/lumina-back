from typing import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import BranchQueryExpansion


def add(session: AsyncSession, expansion: BranchQueryExpansion) -> None:
    session.add(expansion)


async def list_active_grouped(
    session: AsyncSession, branch_ids: Sequence[UUID]
) -> dict[UUID, list[BranchQueryExpansion]]:
    if not branch_ids:
        return {}

    stmt = select(BranchQueryExpansion).where(
        BranchQueryExpansion.branch_id.in_(branch_ids),
        BranchQueryExpansion.is_active.is_(True),
    )
    result = await session.scalars(stmt)

    grouped: dict[UUID, list[BranchQueryExpansion]] = {}
    for expansion in result.all():
        grouped.setdefault(expansion.branch_id, []).append(expansion)
    return grouped


async def deactivate_active(session: AsyncSession, branch_id: UUID) -> None:
    stmt = (
        update(BranchQueryExpansion)
        .where(
            BranchQueryExpansion.branch_id == branch_id,
            BranchQueryExpansion.is_active.is_(True),
        )
        .values(is_active=False)
    )
    await session.execute(stmt)


async def get_latest_generation_version(
    session: AsyncSession, branch_id: UUID
) -> int:
    stmt = select(BranchQueryExpansion.generation_version).where(
        BranchQueryExpansion.branch_id == branch_id
    )
    result = await session.scalars(stmt)
    versions = result.all()
    return max(versions) if versions else 0
