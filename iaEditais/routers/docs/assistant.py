from uuid import UUID

from fastapi import APIRouter

from iaEditais.core.dependencies import Model, Session
from iaEditais.repositories import chat_repo
from iaEditais.services import assistant_service

router = APIRouter(
    prefix='/doc/{doc_id}/assistant',
    tags=['assistente ia, chat'],
)


@router.post('/chat')
async def chat_with_document(
    doc_id: UUID,
    body: dict,
    session: Session,
    model: Model,
):
    message = body.get('message', '')
    history = body.get('history', [])
    conversation_id = body.get('conversation_id')

    conv_uuid = UUID(conversation_id) if conversation_id else None

    result = await assistant_service.chat_with_document(
        doc_id=doc_id,
        message=message,
        history=history,
        model=model,
        session=session,
        conversation_id=conv_uuid,
    )

    if conv_uuid:
        await chat_repo.create_message(session, conv_uuid, 'user', message)
        await chat_repo.create_message(session, conv_uuid, 'assistant', result['response'])
        await chat_repo.update_conversation_timestamp(session, conv_uuid)
        await session.commit()

    return {
        'response': result['response'],
        'conversation_id': conversation_id,
    }
