from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import ChatConversation, ChatMessage


async def create_conversation(
    session: AsyncSession, document_id: UUID, user_id: UUID
) -> ChatConversation:
    conversation = ChatConversation(
        document_id=document_id,
        user_id=user_id,
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def get_conversations_by_user(
    session: AsyncSession, user_id: UUID
) -> list[ChatConversation]:
    stmt = (
        select(ChatConversation)
        .where(
            ChatConversation.user_id == user_id,
            ChatConversation.deleted_at.is_(None),
        )
        .options(selectinload(ChatConversation.document))
        .order_by(ChatConversation.created_at.desc())
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def get_conversation_by_id(
    session: AsyncSession, conversation_id: UUID
) -> ChatConversation | None:
    stmt = (
        select(ChatConversation)
        .where(
            ChatConversation.id == conversation_id,
            ChatConversation.deleted_at.is_(None),
        )
        .options(
            selectinload(ChatConversation.document),
            selectinload(ChatConversation.messages),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_messages_by_conversation(
    session: AsyncSession, conversation_id: UUID
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def create_message(
    session: AsyncSession,
    conversation_id: UUID,
    role: str,
    content: str,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    session.add(message)
    await session.flush()
    return message


async def soft_delete_conversation(
    session: AsyncSession, conversation_id: UUID
) -> bool:
    stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    if not conversation:
        return False
    conversation.deleted_at = func.now()
    return True


async def update_conversation_timestamp(
    session: AsyncSession, conversation_id: UUID
) -> None:
    stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    if conversation:
        conversation.updated_at = func.now()


async def update_conversation_context(
    session: AsyncSession, conversation_id: UUID, context_text: str
) -> None:
    stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
    result = await session.execute(stmt)
    conversation = result.scalar_one_or_none()
    if conversation:
        conversation.context_text = context_text
        conversation.updated_at = func.now()
