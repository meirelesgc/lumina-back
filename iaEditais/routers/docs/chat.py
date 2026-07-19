from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import ChatConversation, Document, DocumentHistory, DocumentRelease
from iaEditais.repositories import chat_repo

router = APIRouter(prefix='/chat', tags=['Chat'])


@router.post('/conversations')
async def create_conversation(
    body: dict,
    session: Session,
    current_user: CurrentUser,
):
    document_id = body.get('document_id')
    if not document_id:
        raise HTTPException(status_code=422, detail='document_id is required')
    conversation = await chat_repo.create_conversation(
        session, UUID(document_id), current_user.id
    )
    await session.commit()
    return {
        'id': str(conversation.id),
        'document_id': str(conversation.document_id),
        'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
    }


@router.get('/conversations')
async def list_conversations(
    session: Session,
    current_user: CurrentUser,
):
    latest_release_subq = (
        select(DocumentRelease)
        .join(DocumentHistory)
        .where(DocumentHistory.document_id == Document.id)
        .order_by(DocumentRelease.created_at.desc())
        .limit(1)
        .lateral()
    )
    latest_release_alias = aliased(DocumentRelease, latest_release_subq)

    stmt = (
        select(
            ChatConversation,
            Document.name,
            Document.identifier,
            latest_release_alias.file_path,
        )
        .join(Document, Document.id == ChatConversation.document_id)
        .join(latest_release_alias, true())
        .where(
            ChatConversation.user_id == current_user.id,
            ChatConversation.deleted_at.is_(None),
        )
        .order_by(ChatConversation.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'id': str(row[0].id),
            'document_id': str(row[0].document_id),
            'document_name': row[1],
            'document_identifier': row[2],
            'file_url': row[3],
            'created_at': row[0].created_at.isoformat() if row[0].created_at else None,
        }
        for row in rows
    ]


@router.get('/conversations/{conversation_id}/messages')
async def get_messages(
    conversation_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    conversation = await chat_repo.get_conversation_by_id(session, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail='Conversation not found')

    messages = await chat_repo.get_messages_by_conversation(session, conversation_id)
    return [
        {
            'id': str(m.id),
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete('/conversations/{conversation_id}')
async def delete_conversation(
    conversation_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    conversation = await chat_repo.get_conversation_by_id(session, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail='Conversation not found')

    deleted = await chat_repo.soft_delete_conversation(session, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Conversation not found')

    doc = conversation.document
    if doc and not doc.deleted_at:
        doc.set_deletion_audit(current_user.id)

    await session.commit()
    return {'ok': True}
