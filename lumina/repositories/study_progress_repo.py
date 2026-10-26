from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import StudyProgress


async def studied_at_by_attachment(
    session: AsyncSession, project_id: UUID
) -> dict[UUID, datetime]:
    stmt = select(
        StudyProgress.study_attachment_id, StudyProgress.studied_at
    ).where(StudyProgress.project_id == project_id)
    return dict((await session.execute(stmt)).all())


async def mark(
    session: AsyncSession, project_id: UUID, attachment_id: UUID, user_id: UUID
) -> None:
    stmt = (
        insert(StudyProgress)
        .values(
            project_id=project_id,
            study_attachment_id=attachment_id,
            studied_by=user_id,
        )
        .on_conflict_do_nothing()
    )
    await session.execute(stmt)


async def unmark(
    session: AsyncSession, project_id: UUID, attachment_id: UUID
) -> None:
    stmt = delete(StudyProgress).where(
        StudyProgress.project_id == project_id,
        StudyProgress.study_attachment_id == attachment_id,
    )
    await session.execute(stmt)
