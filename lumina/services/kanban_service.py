import logging
from enum import Enum
from http import HTTPStatus
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lumina.models import Document, DocumentHistory, User
from lumina.repositories import kanban_repo, project_document_repo
from lumina.schemas import DocumentPublic, DocumentStatus
from lumina.schemas.document_history import DocumentHistoryPublic
from lumina.services import audit_service
from lumina.workers.utils import send_message


class NotifyTarget(str, Enum):
    EDITORS = 'editors'
    CREATOR = 'creator'
    AUDITORS = 'auditors'


NOTIFICATION_RULES: dict[
    DocumentStatus, dict[str, bool | NotifyTarget | list[NotifyTarget]]
] = {
    DocumentStatus.PENDING: {
        'enabled': False,
        'targets': [],
    },
    DocumentStatus.UNDER_CONSTRUCTION: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
    DocumentStatus.WAITING_FOR_REVIEW: {
        'enabled': True,
        'targets': [NotifyTarget.CREATOR, NotifyTarget.AUDITORS],
    },
    DocumentStatus.COMPLETED: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
}

STATUS_TRANSLATION = {
    DocumentStatus.PENDING: 'Pendente',
    DocumentStatus.UNDER_CONSTRUCTION: 'Em construção',
    DocumentStatus.WAITING_FOR_REVIEW: 'Aguardando revisão',
    DocumentStatus.COMPLETED: 'Concluído',
}


async def _resolve_notification_targets(
    session: AsyncSession, doc: Document, status: DocumentStatus
) -> list[UUID]:
    rules = NOTIFICATION_RULES.get(status, {'enabled': False})
    if not rules['enabled']:
        return []

    targets: list[User] = []
    creator_cache = None

    for target_type in rules['targets']:
        if target_type == NotifyTarget.EDITORS:
            targets.extend(doc.editors)

        elif target_type == NotifyTarget.CREATOR and doc.created_by:
            if not creator_cache:
                creator_cache = await kanban_repo.get_user(
                    session, doc.created_by
                )
            if creator_cache:
                targets.append(creator_cache)

        elif target_type == NotifyTarget.AUDITORS:
            auditors = await kanban_repo.get_auditors(session)
            targets.extend(auditors)

    unique_ids = {user.id for user in targets if user.id}
    return list(unique_ids)


async def _publish_notification(
    session: AsyncSession,
    user_ids: list[UUID],
    doc_name: str,
    status: DocumentStatus,
):
    if not user_ids:
        return

    status_traduzido = STATUS_TRANSLATION.get(status, status.value)
    message_text = (
        f"Olá! O status do documento '{doc_name}' "
        f'foi atualizado para: {status_traduzido}'
    )

    payload = {'user_ids': user_ids, 'message_text': message_text}
    await send_message(payload, session)


async def update_document_status(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    new_status: DocumentStatus,
) -> Document:
    doc = await kanban_repo.get_with_editors(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Document not found'
        )

    old_data = DocumentPublic.model_validate(doc).model_dump(mode='json')

    target_user_ids = await _resolve_notification_targets(
        session, doc, new_status
    )

    history = DocumentHistory(
        document_id=doc.id,
        status=new_status.value,
    )
    history.set_creation_audit(user_id)
    kanban_repo.add_history(session, history)

    await session.flush()
    await session.refresh(history)

    new_data = DocumentPublic.model_validate(doc).model_dump(mode='json')
    new_data['history'].insert(
        0,
        DocumentHistoryPublic.model_validate(history).model_dump(mode='json'),
    )
    doc.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Document.__tablename__,
        record_id=doc.id,
        old_data=old_data,
        new_data=new_data,
    )

    if doc.project_document_id:
        project_doc = await project_document_repo.get_by_id(
            session, doc.project_document_id
        )
        if project_doc and not project_doc.deleted_at:
            project_doc.status = new_status.value
            project_doc.set_update_audit(user_id)

    await session.commit()
    await session.refresh(doc)

    try:
        await _publish_notification(
            session, target_user_ids, doc.name, new_status
        )
    except Exception as e:
        logger.warning('Falha ao enviar notificação WhatsApp: %s', e)

    return doc
