"""CRUD operations for chat messages."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.chat_message.model import ChatMessage, ChatMessageCreate


async def create_chat_message(db: AsyncSession, message: ChatMessageCreate) -> ChatMessage:
    """Create a new chat message.

    Args:
        db: Database session
        message: Message creation data

    Returns:
        Created ChatMessage object
    """
    db_message = ChatMessage.model_validate(message)
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message


async def get_chat_message(db: AsyncSession, message_id: int) -> ChatMessage | None:
    """Get a chat message by ID.

    Args:
        db: Database session
        message_id: Message ID

    Returns:
        ChatMessage object or None if not found
    """
    stmt = select(ChatMessage).where(ChatMessage.id == message_id)
    result = await db.exec(stmt)
    return result.first()


async def get_chat_messages_by_thread(db: AsyncSession, thread_id: int, limit: int | None = None) -> list[ChatMessage]:
    """Get all chat messages for a thread.

    Args:
        db: Database session
        thread_id: Thread ID
        limit: Maximum number of messages to return (most recent first)

    Returns:
        List of ChatMessage objects ordered by created_at
    """
    stmt = select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at)
    if limit:
        stmt = stmt.limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def delete_chat_message(db: AsyncSession, message_id: int) -> bool:
    """Delete a chat message.

    Args:
        db: Database session
        message_id: Message ID

    Returns:
        True if deleted, False if not found
    """
    db_message = await get_chat_message(db, message_id)
    if not db_message:
        return False

    await db.delete(db_message)
    await db.commit()
    return True


async def delete_messages_by_thread(db: AsyncSession, thread_id: int) -> int:
    """Delete all messages in a thread.

    Args:
        db: Database session
        thread_id: Thread ID

    Returns:
        Number of messages deleted
    """
    messages = await get_chat_messages_by_thread(db, thread_id)
    count = len(messages)

    for message in messages:
        await db.delete(message)

    await db.commit()
    return count
