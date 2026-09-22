from typing import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import BranchSectionRequirement


def add(session: AsyncSession, requirement: BranchSectionRequirement) -> None:
    session.add(requirement)


async def get_active_grouped(
    session: AsyncSession, branch_ids: Sequence[UUID]
) -> dict[UUID, BranchSectionRequirement]:
    if not branch_ids:
        return {}

    stmt = select(BranchSectionRequirement).where(
        BranchSectionRequirement.branch_id.in_(branch_ids),
        BranchSectionRequirement.is_active.is_(True),
    )
    result = await session.scalars(stmt)

    return {req.branch_id: req for req in result.all()}


async def deactivate_active(session: AsyncSession, branch_id: UUID) -> None:
    stmt = (
        update(BranchSectionRequirement)
        .where(
            BranchSectionRequirement.branch_id == branch_id,
            BranchSectionRequirement.is_active.is_(True),
        )
        .values(is_active=False)
    )
    await session.execute(stmt)


async def get_latest_generation_version(
    session: AsyncSession, branch_id: UUID
) -> int:
    stmt = select(BranchSectionRequirement.generation_version).where(
        BranchSectionRequirement.branch_id == branch_id
    )
    result = await session.scalars(stmt)
    versions = result.all()
    return max(versions) if versions else 0
