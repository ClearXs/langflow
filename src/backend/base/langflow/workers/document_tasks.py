"""Celery tasks for document processing."""

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select

from langflow.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_celery_session_maker():
    """
    Create a new async session maker for Celery tasks.
    This is necessary because Celery tasks run in a new event loop,
    and the default session maker is bound to the main app's event loop.
    """
    from langflow.services.deps import get_settings_service

    settings_service = get_settings_service()
    settings = settings_service.settings

    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,  # Don't use connection pooling for Celery tasks
        echo=False,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def _trigger_entity_extraction_if_enabled(session, space_id: int, document_id: int):
    """Check space configuration and trigger entity extraction task if auto-extraction is enabled.

    Args:
        session: Database session
        space_id: Space ID
        document_id: Document ID
    """
    from langflow.services.database.models.space import Space

    # Get space configuration
    stmt = select(Space).where(Space.id == space_id)
    result = await session.execute(stmt)
    space = result.scalar_one_or_none()

    if not space:
        logger.warning(f"Space {space_id} not found, skipping entity extraction")
        return

    # Check if knowledge graph and auto entity extraction are enabled
    if space.enable_knowledge_graph and space.auto_entity_extraction:
        logger.info(f"Space {space_id} has auto entity extraction enabled, triggering task for document {document_id}")

        # Import and trigger entity extraction task
        from langflow.tasks.knowledge_graph_tasks import (
            extract_entities_from_document_task,
        )

        # Use Celery async task
        extract_entities_from_document_task.delay(document_id, space_id)
        logger.info(f"Triggered entity extraction task for document {document_id}")
    else:
        logger.debug(
            f"Space {space_id} does not have auto entity extraction enabled "
            f"(enable_knowledge_graph={space.enable_knowledge_graph}, "
            f"auto_entity_extraction={space.auto_entity_extraction})"
        )


@celery_app.task(name="langflow.workers.process_extension_document", bind=True)
def process_extension_document_task(self, individual_document_dict, space_id: int, user_id: str):
    """
    Celery task to process extension document.

    Args:
        individual_document_dict: Document data as dictionary
        space_id: ID of the space
        user_id: ID of the user
    """
    import asyncio

    # Create a new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _process_extension_document(individual_document_dict, space_id, user_id)
        )
    finally:
        loop.close()


async def _process_extension_document(individual_document_dict, space_id: int, user_id: str):
    """Process extension document with new session."""
    from pydantic import BaseModel, ConfigDict, Field

    from langflow.services.task_logging.service import TaskLoggingService

    # Reconstruct the document object from dict
    # You'll need to define the proper model for this
    class DocumentMetadata(BaseModel):
        VisitedWebPageTitle: str
        VisitedWebPageURL: str
        BrowsingSessionId: str
        VisitedWebPageDateWithTimeInISOString: str
        VisitedWebPageReffererURL: str
        VisitedWebPageVisitDurationInMilliseconds: str

    class IndividualDocument(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        metadata: DocumentMetadata
        page_content: str = Field(alias="pageContent")

    individual_document = IndividualDocument(**individual_document_dict)

    async with get_celery_session_maker()() as session:
        task_logger = TaskLoggingService(session, space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_extension_document",
            source="document_processor",
            message=f"Starting processing of extension document from {individual_document.metadata.VisitedWebPageTitle}",
            metadata={
                "document_type": "EXTENSION",
                "url": individual_document.metadata.VisitedWebPageURL,
                "title": individual_document.metadata.VisitedWebPageTitle,
                "user_id": user_id,
            },
        )

        try:
            from langflow.services.docling.document_processors import (
                add_extension_received_document,
            )

            result = await add_extension_received_document(
                session, individual_document, space_id, user_id
            )

            if result:
                await task_logger.log_task_success(
                    log_entry,
                    f"Successfully processed extension document: {individual_document.metadata.VisitedWebPageTitle}",
                    {"document_id": result.id, "content_hash": result.content_hash},
                )
                # Trigger entity extraction (if enabled)
                await _trigger_entity_extraction_if_enabled(session, space_id, result.id)
            else:
                await task_logger.log_task_success(
                    log_entry,
                    f"Extension document already exists (duplicate): {individual_document.metadata.VisitedWebPageTitle}",
                    {"duplicate_detected": True},
                )
        except Exception as e:
            await task_logger.log_task_failure(
                log_entry,
                f"Failed to process extension document: {individual_document.metadata.VisitedWebPageTitle}",
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(f"Error processing extension document: {e!s}")
            raise


@celery_app.task(name="langflow.workers.process_youtube_video", bind=True)
def process_youtube_video_task(self, url: str, space_id: int, user_id: str):
    """
    Celery task to process YouTube video.

    Args:
        url: YouTube video URL
        space_id: ID of the space
        user_id: ID of the user
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_process_youtube_video(url, space_id, user_id))
    finally:
        loop.close()


async def _process_youtube_video(url: str, space_id: int, user_id: str):
    """Process YouTube video with new session."""
    from langflow.services.task_logging.service import TaskLoggingService

    async with get_celery_session_maker()() as session:
        task_logger = TaskLoggingService(session, space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_youtube_video",
            source="document_processor",
            message=f"Starting YouTube video processing for: {url}",
            metadata={"document_type": "YOUTUBE_VIDEO", "url": url, "user_id": user_id},
        )

        try:
            from langflow.services.docling.document_processors import (
                add_youtube_video_document,
            )

            result = await add_youtube_video_document(session, url, space_id, user_id)

            if result:
                await task_logger.log_task_success(
                    log_entry,
                    f"Successfully processed YouTube video: {result.title}",
                    {
                        "document_id": result.id,
                        "video_id": result.document_metadata.get("video_id"),
                        "content_hash": result.content_hash,
                    },
                )
                # Trigger entity extraction (if enabled)
                await _trigger_entity_extraction_if_enabled(session, space_id, result.id)
            else:
                await task_logger.log_task_success(
                    log_entry,
                    f"YouTube video document already exists (duplicate): {url}",
                    {"duplicate_detected": True},
                )
        except Exception as e:
            await task_logger.log_task_failure(
                log_entry,
                f"Failed to process YouTube video: {url}",
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(f"Error processing YouTube video: {e!s}")
            raise


@celery_app.task(name="langflow.workers.process_file_upload", bind=True)
def process_file_upload_task(
    self, file_path: str, filename: str, space_id: int, user_id: str
):
    """
    Celery task to process uploaded file.

    Args:
        file_path: Path to the uploaded file
        filename: Original filename
        space_id: ID of the space
        user_id: ID of the user
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _process_file_upload(file_path, filename, space_id, user_id)
        )
    finally:
        loop.close()


async def _process_file_upload(file_path: str, filename: str, space_id: int, user_id: str):
    """Process file upload with new session."""
    from langflow.services.task_logging.service import TaskLoggingService

    async with get_celery_session_maker()() as session:
        task_logger = TaskLoggingService(session, space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_file_upload",
            source="document_processor",
            message=f"Starting file processing for: {filename}",
            metadata={
                "document_type": "FILE",
                "filename": filename,
                "file_path": file_path,
                "user_id": user_id,
            },
        )

        try:
            from langflow.services.docling.file_processors import (
                process_file_in_background,
            )

            await process_file_in_background(
                file_path,
                filename,
                space_id,
                user_id,
                session,
                task_logger,
                log_entry,
            )
        except Exception as e:
            # Import here to avoid circular dependencies
            from fastapi import HTTPException

            from langflow.services.page_limit.service import PageLimitExceededError

            # For page limit errors, use the detailed message from the exception
            if isinstance(e, PageLimitExceededError):
                error_message = str(e)
            elif isinstance(e, HTTPException) and "page limit" in str(e.detail).lower():
                error_message = str(e.detail)
            else:
                error_message = f"Failed to process file: {filename}"

            await task_logger.log_task_failure(
                log_entry,
                error_message,
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(error_message)
            raise
