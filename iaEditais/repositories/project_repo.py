from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Project
from iaEditais.schemas.project import ProjectFilter


async def get_by_id(
    session: AsyncSession, project_id: UUID
) -> Optional[Project]:
    return await session.get(Project, project_id)


async def list_all(
    session: AsyncSession, filters: ProjectFilter
) -> list[Project]:
    query = (
        select(Project)
        .where(Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )

    if filters.q:
        query = query.where(Project.name.ilike(f'%{filters.q}%'))

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add_project(session: AsyncSession, project: Project) -> None:
    session.add(project)
