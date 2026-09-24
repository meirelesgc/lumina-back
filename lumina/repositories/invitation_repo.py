from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lumina.models import Invitation
from lumina.schemas.invitation import InvitationFilter


def add_invitation(session: AsyncSession, invitation: Invitation) -> None:
    session.add(invitation)


async def get_by_id(
    session: AsyncSession, invitation_id: UUID
) -> Optional[Invitation]:
    stmt = (
        select(Invitation)
        .options(
            selectinload(Invitation.inviter),
            selectinload(Invitation.project),
        )
        .where(
            Invitation.id == invitation_id,
            Invitation.deleted_at.is_(None),
        )
    )
    return await session.scalar(stmt)


async def get_by_token(
    session: AsyncSession, token: str
) -> Optional[Invitation]:
    stmt = (
        select(Invitation)
        .options(
            selectinload(Invitation.inviter),
            selectinload(Invitation.project),
        )
        .where(
            Invitation.token == token,
            Invitation.deleted_at.is_(None),
        )
    )
    return await session.scalar(stmt)


async def get_pending_by_email_and_inviter(
    session: AsyncSession,
    email: str,
    inviter_id: UUID,
    project_id: Optional[UUID] = None,
) -> Optional[Invitation]:
    stmt = select(Invitation).where(
        Invitation.deleted_at.is_(None),
        func.lower(Invitation.email) == func.lower(email),
        Invitation.inviter_id == inviter_id,
        Invitation.status == 'PENDING',
    )
    if project_id:
        stmt = stmt.where(Invitation.project_id == project_id)
    else:
        stmt = stmt.where(Invitation.project_id.is_(None))

    return await session.scalar(stmt)


async def list_by_inviter(
    session: AsyncSession,
    inviter_id: UUID,
    status: Optional[str] = None,
) -> Sequence[Invitation]:
    stmt = (
        select(Invitation)
        .options(
            selectinload(Invitation.inviter),
            selectinload(Invitation.project),
        )
        .where(
            Invitation.inviter_id == inviter_id,
            Invitation.deleted_at.is_(None),
        )
        .order_by(Invitation.created_at.desc())
    )
    if status:
        stmt = stmt.where(Invitation.status == status)

    result = await session.scalars(stmt)
    return result.all()


async def list_all(
    session: AsyncSession, filters: InvitationFilter
) -> Sequence[Invitation]:
    stmt = (
        select(Invitation)
        .options(
            selectinload(Invitation.inviter),
            selectinload(Invitation.project),
        )
        .where(Invitation.deleted_at.is_(None))
        .order_by(Invitation.created_at.desc())
    )

    if filters.inviter_id:
        stmt = stmt.where(Invitation.inviter_id == filters.inviter_id)

    if filters.email:
        stmt = stmt.where(
            func.lower(Invitation.email) == func.lower(filters.email)
        )

    if filters.project_id:
        stmt = stmt.where(Invitation.project_id == filters.project_id)

    if filters.status:
        stmt = stmt.where(Invitation.status == filters.status.value)

    if filters.offset:
        stmt = stmt.offset(filters.offset)
    if filters.limit:
        stmt = stmt.limit(filters.limit)

    result = await session.scalars(stmt)
    return result.all()


async def list_pending_by_email(
    session: AsyncSession,
    email: str,
) -> Sequence[Invitation]:
    stmt = (
        select(Invitation)
        .options(
            selectinload(Invitation.inviter),
            selectinload(Invitation.project),
        )
        .where(
            Invitation.deleted_at.is_(None),
            func.lower(Invitation.email) == func.lower(email),
            Invitation.status == 'PENDING',
            Invitation.expires_at > func.now(),
        )
        .order_by(Invitation.created_at.desc())
    )
    result = await session.scalars(stmt)
    return result.all()
