from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import DocumentGroupItem, StudyAttachment, Typification


def _visible() -> Select:
    """Anexos ativos, de itens ativos, com o nome da tipificação.

    Anexos de tipificação excluída ficam de fora.

    O filtro global de soft delete (`lumina/core/database.py`) tiraria a
    tipificação excluída do join e deixaria o anexo passar com nome nulo.
    A consulta desliga esse filtro e aplica as exclusões por conta própria.
    """
    return (
        select(StudyAttachment, Typification.name)
        .join(
            DocumentGroupItem,
            StudyAttachment.document_group_item_id == DocumentGroupItem.id,
        )
        .outerjoin(
            Typification, StudyAttachment.typification_id == Typification.id
        )
        .where(
            StudyAttachment.deleted_at.is_(None),
            DocumentGroupItem.deleted_at.is_(None),
            or_(
                StudyAttachment.typification_id.is_(None),
                Typification.deleted_at.is_(None),
            ),
        )
        .execution_options(
            populate_existing=True, skip_soft_delete_filter=True
        )
    )


async def get_visible(
    session: AsyncSession, attachment_id: UUID
) -> Optional[tuple[StudyAttachment, Optional[str]]]:
    stmt = _visible().where(StudyAttachment.id == attachment_id)
    return (await session.execute(stmt)).first()


async def list_visible_by_items(
    session: AsyncSession, item_ids: list[UUID]
) -> list[tuple[StudyAttachment, Optional[str]]]:
    stmt = (
        _visible()
        .where(StudyAttachment.document_group_item_id.in_(item_ids))
        .order_by(StudyAttachment.position)
    )
    return (await session.execute(stmt)).all()


async def next_position(session: AsyncSession, item_id: UUID) -> int:
    stmt = select(func.coalesce(func.max(StudyAttachment.position), 0)).where(
        StudyAttachment.document_group_item_id == item_id,
        StudyAttachment.deleted_at.is_(None),
    )
    return await session.scalar(stmt) + 1


async def exists_in_item(
    session: AsyncSession,
    item_id: UUID,
    column: Any,
    value: Any,
    exclude_id: Optional[UUID] = None,
) -> bool:
    stmt = select(StudyAttachment.id).where(
        StudyAttachment.document_group_item_id == item_id,
        StudyAttachment.deleted_at.is_(None),
        column == value,
    )
    if exclude_id:
        stmt = stmt.where(StudyAttachment.id != exclude_id)
    return await session.scalar(stmt) is not None


def add(session: AsyncSession, attachment: StudyAttachment) -> None:
    session.add(attachment)
