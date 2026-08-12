from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import ProjectDocument


async def get_by_id(
    session: AsyncSession, doc_id: UUID
) -> Optional[ProjectDocument]:
    return await session.get(ProjectDocument, doc_id)


async def get_by_project(
    session: AsyncSession, project_id: UUID
) -> list[ProjectDocument]:
    stmt = (
        select(ProjectDocument)
        .where(
            ProjectDocument.project_id == project_id,
            ProjectDocument.deleted_at.is_(None),
        )
        .order_by(ProjectDocument.created_at.desc())
    )
    result = await session.scalars(stmt)
    return result.all()


def add_document(
    session: AsyncSession, document: ProjectDocument
) -> None:
    session.add(document)
