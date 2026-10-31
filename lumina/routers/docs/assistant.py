from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from lumina.core.dependencies import CurrentUser, Model, Session
from lumina.core.security import get_current_user
from lumina.repositories import chat_repo
from lumina.services import assistant_service, doc_service

router = APIRouter(
    prefix='/doc/{doc_id}/assistant',
    tags=['assistente ia, chat'],
    dependencies=[Depends(get_current_user)],
)


@router.post('/chat')
async def chat_with_document(
    doc_id: UUID,
    body: dict,
    session: Session,
    model: Model,
    current_user: CurrentUser,
):
    await doc_service.get_doc_by_id(session, current_user, doc_id)

    message = body.get('message', '')
    history = body.get('history', [])
    conversation_id = body.get('conversation_id')

    conv_uuid = UUID(conversation_id) if conversation_id else None
    if conv_uuid:
        conversation = await chat_repo.get_conversation_by_id(
            session, conv_uuid
        )
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Conversation not found',
            )

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
        await chat_repo.create_message(
            session, conv_uuid, 'assistant', result['response']
        )
        await chat_repo.update_conversation_timestamp(session, conv_uuid)
        await session.commit()

    return {
        'response': result['response'],
        'conversation_id': conversation_id,
    }
