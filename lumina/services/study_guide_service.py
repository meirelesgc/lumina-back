from collections import defaultdict
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import Project, User
from lumina.repositories import (
    document_group_repo,
    study_attachment_repo,
    study_progress_repo,
)
from lumina.schemas.study_guide import (
    StudyGuideAttachment,
    StudyGuideGroup,
    StudyGuideItem,
    StudyGuidePublic,
)
from lumina.services import project_service
from lumina.services.study_attachment_service import to_public


async def _active_items(session: AsyncSession, project: Project):
    if not project.document_group_id:
        return None, []
    group = await document_group_repo.get_by_id(
        session, project.document_group_id
    )
    if not group or group.deleted_at:
        return None, []
    return group, group.items


async def _build_guide(
    session: AsyncSession, project: Project
) -> StudyGuidePublic:
    group, items = await _active_items(session, project)
    if not group:
        return StudyGuidePublic(project_id=project.id)

    rows = await study_attachment_repo.list_visible_by_items(
        session, [item.id for item in items]
    )
    studied_at = await study_progress_repo.studied_at_by_attachment(
        session, project.id
    )

    attachments_by_item = defaultdict(list)
    for attachment, typification_name in rows:
        attachments_by_item[attachment.document_group_item_id].append(
            StudyGuideAttachment(
                **to_public(attachment, typification_name).model_dump(),
                studied=attachment.id in studied_at,
                studied_at=studied_at.get(attachment.id),
            )
        )

    guide_items = [
        StudyGuideItem(
            id=item.id,
            name=item.name,
            icon_path=item.icon_path,
            position=item.position,
            attachments=attachments_by_item[item.id],
        )
        for item in items
    ]
    return StudyGuidePublic(
        project_id=project.id,
        document_group=StudyGuideGroup(id=group.id, name=group.name),
        items=guide_items,
        total_attachments=len(rows),
        studied_attachments=sum(
            1 for attachment, _ in rows if attachment.id in studied_at
        ),
    )


async def get_study_guide(
    session: AsyncSession, current_user: User, project_id: UUID
) -> StudyGuidePublic:
    project = await project_service.get_project_by_id(
        session, current_user, project_id
    )
    return await _build_guide(session, project)


async def set_studied(
    session: AsyncSession,
    current_user: User,
    project_id: UUID,
    attachment_id: UUID,
    studied: bool,
) -> StudyGuidePublic:
    project = await project_service.get_project_by_id(
        session, current_user, project_id
    )
    if project.created_by != current_user.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Só o dono do projeto marca o que estudou.',
        )

    _, items = await _active_items(session, project)
    row = await study_attachment_repo.get_visible(session, attachment_id)
    if not row or row[0].document_group_item_id not in {i.id for i in items}:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Study attachment not found in the project guide',
        )

    if studied:
        await study_progress_repo.mark(
            session, project.id, attachment_id, current_user.id
        )
    else:
        await study_progress_repo.unmark(session, project.id, attachment_id)
    await session.commit()

    return await _build_guide(session, project)
