from http import HTTPStatus
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import DocumentGroupItem, StudyAttachment
from lumina.repositories import (
    document_group_repo,
    study_attachment_repo,
    typification_repo,
)
from lumina.schemas.study_attachment import (
    StudyAttachmentCreate,
    StudyAttachmentKind,
    StudyAttachmentOrder,
    StudyAttachmentPublic,
    StudyAttachmentSchema,
    StudyAttachmentUpdate,
    TypificationRef,
)
from lumina.services import crossref_client


def to_public(
    attachment: StudyAttachment, typification_name: Optional[str]
) -> StudyAttachmentPublic:
    typification = None
    if attachment.typification_id:
        typification = TypificationRef(
            id=attachment.typification_id, name=typification_name
        )
    return StudyAttachmentPublic(
        id=attachment.id,
        document_group_item_id=attachment.document_group_item_id,
        kind=attachment.kind,
        position=attachment.position,
        description=attachment.description,
        title=attachment.title,
        typification=typification,
        doi=attachment.doi,
        doi_url=f'https://doi.org/{attachment.doi}'
        if attachment.doi
        else None,
        authors=attachment.authors or [],
        year=attachment.year,
        container_title=attachment.container_title,
        metadata_source=attachment.metadata_source,
        url=attachment.url,
        created_at=attachment.created_at,
        updated_at=attachment.updated_at,
    )


async def _get_active_item(
    session: AsyncSession, item_id: UUID
) -> DocumentGroupItem:
    item = await document_group_repo.get_item_by_id(session, item_id)
    if not item or item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )
    return item


async def _get_visible(
    session: AsyncSession, attachment_id: UUID
) -> StudyAttachment:
    row = await study_attachment_repo.get_visible(session, attachment_id)
    if not row:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Study attachment not found',
        )
    return row[0]


async def _ensure_unique(session, attachment, column, value) -> None:
    if await study_attachment_repo.exists_in_item(
        session,
        attachment.document_group_item_id,
        column,
        value,
        exclude_id=attachment.id,
    ):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='The item already has this study attachment',
        )


async def _apply(
    session: AsyncSession,
    attachment: StudyAttachment,
    data: StudyAttachmentSchema,
) -> Optional[str]:
    """Grava os campos do tipo e devolve o nome da tipificação, se houver."""
    attachment.description = data.description

    if data.kind == StudyAttachmentKind.TYPIFICATION:
        typification = None
        if data.typification_id:
            typification = await typification_repo.get_by_id(
                session, data.typification_id
            )
        if not typification or typification.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail='Typification not found',
            )
        await _ensure_unique(
            session,
            attachment,
            StudyAttachment.typification_id,
            typification.id,
        )
        attachment.typification_id = typification.id
        return typification.name

    if data.kind == StudyAttachmentKind.DOI:
        await _ensure_unique(
            session, attachment, StudyAttachment.doi, data.doi
        )
        if data.doi == attachment.doi:
            if data.title is not None:
                attachment.title = data.title
            return None

        metadata = await crossref_client.fetch_doi_metadata(data.doi)
        attachment.doi = data.doi
        attachment.title = data.title or (metadata.title if metadata else None)
        attachment.authors = metadata.authors if metadata else []
        attachment.year = metadata.year if metadata else None
        attachment.container_title = (
            metadata.container_title if metadata else None
        )
        attachment.metadata_source = 'CROSSREF' if metadata else 'MANUAL'
        return None

    await _ensure_unique(session, attachment, StudyAttachment.url, data.url)
    attachment.url = data.url
    attachment.title = data.title
    return None


async def create_attachment(
    session: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    data: StudyAttachmentCreate,
) -> StudyAttachmentPublic:
    await _get_active_item(session, item_id)

    attachment = StudyAttachment(
        document_group_item_id=item_id,
        kind=data.kind.value,
        position=await study_attachment_repo.next_position(session, item_id),
    )
    typification_name = await _apply(session, attachment, data)
    attachment.set_creation_audit(user_id)
    study_attachment_repo.add(session, attachment)

    await session.commit()
    await session.refresh(attachment)
    return to_public(attachment, typification_name)


async def list_attachments(
    session: AsyncSession, item_id: UUID
) -> list[StudyAttachmentPublic]:
    await _get_active_item(session, item_id)
    rows = await study_attachment_repo.list_visible_by_items(
        session, [item_id]
    )
    return [to_public(attachment, name) for attachment, name in rows]


async def update_attachment(
    session: AsyncSession, user_id: UUID, data: StudyAttachmentUpdate
) -> StudyAttachmentPublic:
    attachment = await _get_visible(session, data.id)
    if data.kind.value != attachment.kind:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='The kind of a study attachment cannot change',
        )

    await _apply(session, attachment, data)
    attachment.set_update_audit(user_id)

    await session.commit()
    _, typification_name = await study_attachment_repo.get_visible(
        session, attachment.id
    )
    return to_public(attachment, typification_name)


async def reorder_attachments(
    session: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    data: StudyAttachmentOrder,
) -> list[StudyAttachmentPublic]:
    await _get_active_item(session, item_id)
    rows = await study_attachment_repo.list_visible_by_items(
        session, [item_id]
    )

    by_id = {attachment.id: attachment for attachment, _ in rows}
    if len(data.attachment_ids) != len(by_id) or set(
        data.attachment_ids
    ) != set(by_id):
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='attachment_ids must list each attachment of the item once',
        )

    for position, attachment_id in enumerate(data.attachment_ids, start=1):
        by_id[attachment_id].position = position
        by_id[attachment_id].set_update_audit(user_id)

    await session.commit()
    return await list_attachments(session, item_id)


async def delete_attachment(
    session: AsyncSession, user_id: UUID, attachment_id: UUID
) -> None:
    attachment = await _get_visible(session, attachment_id)
    attachment.set_deletion_audit(user_id)
    await session.commit()
