from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import (
    AccessType,
    Advisorship,
    Document,
    Project,
    ProjectDocument,
    User,
)
from lumina.schemas.project import ProjectFilter, ProjectScope


async def get_by_id(
    session: AsyncSession, project_id: UUID
) -> Optional[Project]:
    return await session.get(Project, project_id)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: Optional[UUID] = None
) -> Optional[Project]:
    stmt = select(Project).where(
        Project.deleted_at.is_(None), Project.name == name
    )
    if exclude_id:
        stmt = stmt.where(Project.id != exclude_id)
    return await session.scalar(stmt)


async def has_project_access(
    session: AsyncSession, current_user: User, project: Project
) -> bool:
    if current_user.access_level == AccessType.ADMIN:
        return True

    if project.created_by == current_user.id:
        return True

    if project.created_by:
        stmt = select(Advisorship.id).where(
            Advisorship.advisor_id == current_user.id,
            Advisorship.advisee_id == project.created_by,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )
        if await session.scalar(stmt):
            return True

    return False


async def list_all(
    session: AsyncSession, current_user: User, filters: ProjectFilter
) -> list[Project]:
    query = (
        select(Project)
        .where(Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )

    is_admin = current_user.access_level == AccessType.ADMIN

    if is_admin:
        if filters.scope == ProjectScope.MINE:
            query = query.where(Project.created_by == current_user.id)
    else:
        advisee_ids_subq = select(Advisorship.advisee_id).where(
            Advisorship.advisor_id == current_user.id,
            Advisorship.status == 'ACTIVE',
            Advisorship.deleted_at.is_(None),
        )

        if filters.scope == ProjectScope.ADVISEES:
            query = query.where(Project.created_by.in_(advisee_ids_subq))
        elif filters.scope == ProjectScope.ALL:
            query = query.where(
                (Project.created_by == current_user.id)
                | (Project.created_by.in_(advisee_ids_subq))
            )
        else:
            # Default: MINE (apenas os projetos criados pelo usuario)
            query = query.where(Project.created_by == current_user.id)

    if filters.q:
        query = query.where(Project.name.ilike(f'%{filters.q}%'))

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add_project(session: AsyncSession, project: Project) -> None:
    session.add(project)


async def update_document_project_names(
    session: AsyncSession,
    project_id: UUID,
    old_name: str,
    new_name: str,
) -> None:
    project_document_ids = select(ProjectDocument.id).where(
        ProjectDocument.project_id == project_id
    )
    await session.execute(
        update(Document)
        .where(
            or_(
                Document.projeto_nome == old_name,
                Document.project_document_id.in_(project_document_ids),
            )
        )
        .values(projeto_nome=new_name)
    )
