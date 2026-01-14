"""CRUD operations for chat threads."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.chat_thread.model import ChatThread, ChatThreadCreate, ChatThreadUpdate


async def create_chat_thread(db: AsyncSession, thread: ChatThreadCreate) -> ChatThread:
    """Create a new chat thread.

    Args:
        db: Database session
        thread: Thread creation data

    Returns:
        Created ChatThread object
    """
    db_thread = ChatThread.model_validate(thread)
    db.add(db_thread)
    await db.commit()
    await db.refresh(db_thread)
    return db_thread


async def get_chat_thread(db: AsyncSession, thread_id: int) -> ChatThread | None:
    """Get a chat thread by ID.

    Args:
        db: Database session
        thread_id: Thread ID

    Returns:
        ChatThread object or None if not found
    """
    stmt = select(ChatThread).where(ChatThread.id == thread_id)
    result = await db.exec(stmt)
    return result.first()


async def get_chat_threads_by_space(db: AsyncSession, space_id: int, include_archived: bool = False) -> list[ChatThread]:
    """Get all chat threads for a space.

    Args:
        db: Database session
        space_id: Space ID
        include_archived: Include archived threads

    Returns:
        List of ChatThread objects
    """
    stmt = select(ChatThread).where(ChatThread.space_id == space_id)
    if not include_archived:
        stmt = stmt.where(ChatThread.archived == False)  # noqa: E712
    stmt = stmt.order_by(ChatThread.updated_at.desc())
    result = await db.exec(stmt)
    return list(result.all())


async def update_chat_thread(db: AsyncSession, thread_id: int, thread_update: ChatThreadUpdate) -> ChatThread:
    """Update a chat thread.

    Args:
        db: Database session
        thread_id: Thread ID
        thread_update: Thread update data

    Returns:
        Updated ChatThread object

    Raises:
        HTTPException: If thread not found
    """
    db_thread = await get_chat_thread(db, thread_id)
    if not db_thread:
        raise HTTPException(status_code=404, detail="Chat thread not found")

    thread_data = thread_update.model_dump(exclude_unset=True)
    for key, value in thread_data.items():
        setattr(db_thread, key, value)

    db_thread.updated_at = datetime.now(timezone.utc)
    flag_modified(db_thread, "updated_at")

    await db.commit()
    await db.refresh(db_thread)
    return db_thread


async def delete_chat_thread(db: AsyncSession, thread_id: int) -> bool:
    """Delete a chat thread.

    Args:
        db: Database session
        thread_id: Thread ID

    Returns:
        True if deleted, False if not found
    """
    db_thread = await get_chat_thread(db, thread_id)
    if not db_thread:
        return False

    await db.delete(db_thread)
    await db.commit()
    return True
