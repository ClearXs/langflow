"""Celery tasks for document processing."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select

from langflow.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_celery_session_maker():
    """Create a new async session maker for Celery tasks.
    This is necessary because Celery tasks run in a new event loop,
    and the default session maker is bound to the main app's event loop.
    """
    from langflow.services.deps import get_settings_service

    settings_service = get_settings_service()
    settings = settings_service.settings

    # Convert sync database URL to async if needed
    database_url = settings.database_url
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        database_url,
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

        # Check which extraction method to use (LightRAG or traditional)
        from langflow.services.graph.config import kg_config

        if kg_config.enabled and kg_config.is_available():
            # Use LightRAG for graph extraction
            logger.info(f"Using LightRAG for graph extraction (document {document_id})")
            from langflow.tasks.lightrag_graph_tasks import extract_lightrag_graph_task

            extract_lightrag_graph_task.delay(document_id, space_id)
        else:
            # Fallback to traditional entity extraction
            logger.info(f"Using traditional entity extraction (document {document_id})")
            from langflow.tasks.knowledge_graph_tasks import (
                extract_entities_from_document_task,
            )

            extract_entities_from_document_task.delay(document_id, space_id)

        logger.info(f"Triggered knowledge graph extraction task for document {document_id}")
    else:
        logger.debug(
            f"Space {space_id} does not have auto entity extraction enabled "
            f"(enable_knowledge_graph={space.enable_knowledge_graph}, "
            f"auto_entity_extraction={space.auto_entity_extraction})"
        )


@celery_app.task(name="langflow.workers.process_extension_document", bind=True)
def process_extension_document_task(self, individual_document_dict, space_id: int, user_id: str):
    """Celery task to process extension document.

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
        loop.run_until_complete(_process_extension_document(individual_document_dict, space_id, user_id))
    finally:
        loop.close()


async def _process_extension_document(individual_document_dict, space_id: int, user_id: str):
    """Process extension document with new session."""
    from pydantic import BaseModel, ConfigDict, Field

    from langflow.services.task_logging.task_logging_service import TaskLoggingService

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

            result = await add_extension_received_document(session, individual_document, space_id, user_id)

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
def process_youtube_video_task(self, document_id: int, video_url: str, video_id: str):
    """Celery task to process YouTube video.

    Args:
        document_id: Document ID
        video_url: YouTube video URL
        video_id: YouTube video ID
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_process_youtube_video(document_id, video_url, video_id))
    finally:
        loop.close()


async def _process_youtube_video(document_id: int, video_url: str, video_id: str):
    """Process YouTube video with new session."""
    import hashlib
    from datetime import datetime

    from sqlmodel import select

    from langflow.services.database.models.document.model import Document
    from langflow.services.task_logging.task_logging_service import TaskLoggingService

    async with get_celery_session_maker()() as session:
        # Get the document
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            logger.error(f"Document {document_id} not found")
            return

        task_logger = TaskLoggingService(session, document.space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_youtube_video",
            source="document_processor",
            message=f"Starting YouTube video processing for: {video_url}",
            metadata={
                "document_id": document_id,
                "document_type": "YOUTUBE",
                "url": video_url,
                "video_id": video_id,
            },
        )

        try:
            # Update status
            document.processing_status = "processing"
            await session.commit()

            # Extract YouTube transcript
            try:
                from youtube_transcript_api import YouTubeTranscriptApi

                # Get transcript
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

                # Combine transcript segments
                transcript_text = "\n".join([segment["text"] for segment in transcript_list])

                # Get video metadata (using pytube or youtube-dl would be alternatives)
                video_title = f"YouTube Video: {video_id}"

                # Update document
                document.title = video_title
                document.content = transcript_text
                document.content_hash = hashlib.sha256(transcript_text.encode()).hexdigest()
                document.processing_status = "completed"
                document.indexed_at = datetime.utcnow()

                await session.commit()

                await task_logger.log_task_success(
                    log_entry,
                    f"Successfully processed YouTube video: {video_title}",
                    {
                        "document_id": document.id,
                        "video_id": video_id,
                        "content_hash": document.content_hash,
                        "transcript_segments": len(transcript_list),
                    },
                )

                # Trigger entity extraction
                await _trigger_entity_extraction_if_enabled(session, document.space_id, document.id)

            except Exception as transcript_error:
                # Handle transcript not available
                document.processing_status = "failed"
                document.processing_error = f"Transcript not available: {transcript_error!s}"
                await session.commit()

                await task_logger.log_task_failure(
                    log_entry,
                    f"Failed to extract YouTube transcript: {video_url}",
                    str(transcript_error),
                    {"error_type": type(transcript_error).__name__},
                )
                logger.error(f"Transcript extraction failed for {video_url}: {transcript_error}")
                raise

        except Exception as e:
            document.processing_status = "failed"
            document.processing_error = str(e)
            await session.commit()

            await task_logger.log_task_failure(
                log_entry,
                f"Failed to process YouTube video: {video_url}",
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(f"Error processing YouTube video {video_url}: {e}")
            raise


@celery_app.task(name="langflow.workers.process_web_crawl", bind=True)
def process_web_crawl_task(self, document_id: int, url: str, crawl_subpages: bool, max_depth: int):
    """Celery task to process web page crawling.

    Args:
        document_id: Document ID
        url: Web page URL to crawl
        crawl_subpages: Whether to crawl subpages
        max_depth: Maximum depth for crawling subpages (1-3)
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_process_web_crawl(document_id, url, crawl_subpages, max_depth))
    finally:
        loop.close()


async def _process_web_crawl(document_id: int, url: str, crawl_subpages: bool, max_depth: int):
    """Process web page crawling with new session."""
    import hashlib
    from datetime import datetime
    from urllib.parse import urljoin, urlparse

    import aiohttp
    from bs4 import BeautifulSoup
    from sqlmodel import select

    from langflow.services.database.models.document.model import Document
    from langflow.services.task_logging.task_logging_service import TaskLoggingService

    async with get_celery_session_maker()() as session:
        # Get the document
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            logger.error(f"Document {document_id} not found")
            return

        task_logger = TaskLoggingService(session, document.space_id)

        log_entry = await task_logger.log_task_start(
            task_name="process_web_crawl",
            source="document_processor",
            message=f"Starting web crawl for: {url}",
            metadata={
                "document_id": document_id,
                "document_type": "WEB_PAGE",
                "url": url,
                "crawl_subpages": crawl_subpages,
                "max_depth": max_depth,
            },
        )

        try:
            # Update status
            document.processing_status = "processing"
            await session.commit()

            # Fetch and parse web page
            async with aiohttp.ClientSession() as http_session:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; Langflow/1.0; +https://langflow.com)"}

                async with http_session.get(url, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    html_content = await response.text()

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract page title
            page_title = soup.title.string if soup.title else url

            # Extract main content
            main_content = soup.get_text(separator="\n", strip=True)

            # Clean up content (remove excessive whitespace)
            lines = [line.strip() for line in main_content.splitlines()]
            content = "\n".join(line for line in lines if line)

            # Update document
            document.title = page_title[:500]  # Limit title length
            document.content = content
            document.content_hash = hashlib.sha256(content.encode()).hexdigest()
            document.processing_status = "completed"
            document.indexed_at = datetime.utcnow()

            await session.commit()

            # Handle subpage crawling (if enabled)
            crawled_urls = [url]
            if crawl_subpages and max_depth > 1:
                logger.info(f"Crawling subpages for {url} with max_depth={max_depth}")

                # Find all links on the page
                base_domain = urlparse(url).netloc
                links = set()

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(url, href)

                    # Only crawl links on the same domain
                    if urlparse(full_url).netloc == base_domain:
                        links.add(full_url)

                # Limit number of subpages (prevent excessive crawling)
                max_subpages = 10 * max_depth
                subpage_urls = list(links - set(crawled_urls))[:max_subpages]

                logger.info(f"Found {len(subpage_urls)} subpages to crawl (max={max_subpages})")

                # Crawl subpages (create new documents)
                for subpage_url in subpage_urls:
                    try:
                        # Generate unique identifier hash
                        unique_id_hash = hashlib.sha256(
                            f"{document.space_id}_webpage_{subpage_url}".encode()
                        ).hexdigest()

                        # Check if already exists
                        check_stmt = select(Document).filter(
                            Document.unique_identifier_hash == unique_id_hash,
                            Document.space_id == document.space_id,
                        )
                        check_result = await session.execute(check_stmt)
                        existing = check_result.scalars().first()

                        if existing:
                            logger.debug(f"Subpage {subpage_url} already exists, skipping")
                            continue

                        # Fetch subpage
                        async with http_session.get(subpage_url, headers=headers, timeout=30) as subpage_response:
                            subpage_response.raise_for_status()
                            subpage_html = await subpage_response.text()

                        # Parse subpage
                        subpage_soup = BeautifulSoup(subpage_html, "html.parser")

                        for script in subpage_soup(["script", "style", "nav", "footer", "header"]):
                            script.decompose()

                        subpage_title = subpage_soup.title.string if subpage_soup.title else subpage_url
                        subpage_content = subpage_soup.get_text(separator="\n", strip=True)
                        subpage_lines = [line.strip() for line in subpage_content.splitlines()]
                        subpage_clean = "\n".join(line for line in subpage_lines if line)

                        # Create subpage document
                        subpage_doc = Document(
                            connector_id=document.connector_id,
                            space_id=document.space_id,
                            user_id=document.user_id,
                            title=subpage_title[:500],
                            content=subpage_clean,
                            url=subpage_url,
                            doc_type="WEB_PAGE",
                            content_hash=hashlib.sha256(subpage_clean.encode()).hexdigest(),
                            unique_identifier_hash=unique_id_hash,
                            document_metadata={
                                "url": subpage_url,
                                "parent_url": url,
                                "crawl_depth": 1,
                                "source": "web_crawl_subpage",
                            },
                            processing_status="completed",
                            indexed_at=datetime.utcnow(),
                        )

                        session.add(subpage_doc)
                        await session.flush()

                        logger.info(f"Created subpage document: {subpage_doc.id} for {subpage_url}")

                        # Trigger entity extraction for subpage
                        await _trigger_entity_extraction_if_enabled(session, document.space_id, subpage_doc.id)

                        crawled_urls.append(subpage_url)

                    except Exception as subpage_error:
                        logger.warning(f"Failed to crawl subpage {subpage_url}: {subpage_error}")
                        # Continue with other subpages
                        continue

                await session.commit()

            await task_logger.log_task_success(
                log_entry,
                f"Successfully crawled web page: {page_title}",
                {
                    "document_id": document.id,
                    "content_hash": document.content_hash,
                    "crawled_urls_count": len(crawled_urls),
                    "crawled_urls": crawled_urls,
                },
            )

            # Trigger entity extraction for main page
            await _trigger_entity_extraction_if_enabled(session, document.space_id, document.id)

        except aiohttp.ClientError as e:
            document.processing_status = "failed"
            document.processing_error = f"HTTP error: {e!s}"
            await session.commit()

            await task_logger.log_task_failure(
                log_entry,
                f"Failed to fetch web page: {url}",
                str(e),
                {"error_type": "ClientError"},
            )
            logger.error(f"Error fetching web page {url}: {e}")
            raise

        except Exception as e:
            document.processing_status = "failed"
            document.processing_error = str(e)
            await session.commit()

            await task_logger.log_task_failure(
                log_entry,
                f"Failed to process web page: {url}",
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(f"Error processing web page {url}: {e}")
            raise


@celery_app.task(name="langflow.workers.process_file_upload", bind=True)
def process_file_upload_task(self, file_path: str, filename: str, space_id: int, user_id: str):
    """Celery task to process uploaded file.

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
        loop.run_until_complete(_process_file_upload(file_path, filename, space_id, user_id))
    finally:
        loop.close()


async def _process_file_upload(file_path: str, filename: str, space_id: int, user_id: str):
    """Process file upload with new session."""
    import hashlib
    import os
    from uuid import UUID

    from langflow.services.database.models.document import Document, DocumentType
    from langflow.services.etl.processors import process_document_with_fallback
    from langflow.services.task_logging.task_logging_service import TaskLoggingService

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
            # Process document with ETL
            logger.info(f"Processing file: {filename}")
            markdown_content, service_used = await process_document_with_fallback(file_path)

            logger.info(f"File processed successfully with {service_used}, content length: {len(markdown_content)}")

            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(markdown_content.encode()).hexdigest()

            # Create unique identifier hash (based on filename + space_id)
            unique_identifier = f"{filename}_{space_id}"
            unique_identifier_hash = hashlib.sha256(unique_identifier.encode()).hexdigest()

            # Convert user_id string to UUID
            user_uuid = UUID(user_id)

            # Detect file type from extension
            file_extension = os.path.splitext(filename)[1].lower()
            file_type_map = {
                ".pdf": ("pdf", DocumentType.PDF),
                ".docx": ("docx", DocumentType.NOTE),  # Use NOTE for editable docs
                ".doc": ("doc", DocumentType.NOTE),
                ".txt": ("txt", DocumentType.NOTE),
                ".md": ("markdown", DocumentType.NOTE),
                ".json": ("json", DocumentType.NOTE),
                ".csv": ("csv", DocumentType.NOTE),
                ".xlsx": ("xlsx", DocumentType.NOTE),
                ".xls": ("xls", DocumentType.NOTE),
                ".pptx": ("pptx", DocumentType.NOTE),
                ".ppt": ("ppt", DocumentType.NOTE),
                ".html": ("html", DocumentType.WEBSITE),
                ".xml": ("xml", DocumentType.NOTE),
            }
            detected_file_type, doc_type_enum = file_type_map.get(
                file_extension,
                ("unknown", DocumentType.NOTE),  # Default to NOTE for unknown types
            )

            # Create document record
            # Note: id is auto-generated, don't set it
            # connector_id is required but we don't have a connector for file uploads, so we need to handle this
            # For now, we'll need to create a default connector or make it nullable
            document = Document(
                # id is auto-generated, don't set it
                connector_id=1,  # TODO: Create a default "file_upload" connector or make nullable
                space_id=space_id,
                user_id=user_uuid,
                title=filename,
                content=markdown_content,
                url=None,
                doc_type=doc_type_enum.value,  # Use detected type
                blocknote_document=None,
                content_hash=content_hash,
                unique_identifier_hash=unique_identifier_hash,
                content_needs_reindexing=False,
                document_metadata={
                    "filename": filename,
                    "etl_service": service_used,
                    "user_id": user_id,
                    "original_file_type": detected_file_type,  # Store original type in metadata
                },
                file_name=filename,
                file_type=detected_file_type,  # Store the actual file extension type
                etl_service=service_used,
                processing_status="completed",
            )

            session.add(document)
            await session.commit()
            await session.refresh(document)

            logger.info(f"Document created with ID: {document.id}")

            # ========== Phase 1: Vectorization (Chunking + Embedding) ==========
            try:
                from langflow.services.database.models.chunk.model import Chunk
                from langflow.services.etl.chunking import get_chunking_service
                from langflow.services.etl.embeddings import get_embedding_service

                logger.info(f"Starting vectorization for document {document.id}")

                # Initialize services
                chunking_service = get_chunking_service()
                embedding_service = get_embedding_service()

                # Step 1: Chunk the document content
                chunks_data = await chunking_service.chunk_document(
                    content=markdown_content, file_type=detected_file_type, file_name=filename
                )

                logger.info(f"Created {len(chunks_data)} chunks for document {document.id}")

                if chunks_data:
                    # Step 2: Generate embeddings for chunks (batch processing)
                    chunk_texts = [chunk["content"] for chunk in chunks_data]
                    chunk_embeddings = await embedding_service.embed_batch(chunk_texts)

                    logger.info(f"Generated {len(chunk_embeddings)} embeddings")

                    # Step 3: Generate document-level embedding (first 5000 chars)
                    doc_embedding = await embedding_service.embed_text(markdown_content[:5000])

                    # Step 4: Create Chunk records in database (WITHOUT embeddings)
                    chunks_to_create = []
                    for chunk_data in chunks_data:
                        chunk = Chunk(
                            content=chunk_data["content"],
                            # embedding field removed - vectors will be in Chroma
                            chunk_index=chunk_data["index"],
                            token_count=chunk_data["token_count"],
                            chunk_type=chunk_data["type"],
                            programming_language=chunk_data.get("language"),
                            document_id=document.id,
                            space_id=space_id,
                        )
                        session.add(chunk)
                        chunks_to_create.append(chunk)

                    # Flush to get chunk IDs
                    await session.flush()

                    # Step 5: Store vectors in Chroma
                    try:
                        from langflow.services.vector import VectorMetadata, get_vector_store

                        vector_store = get_vector_store()
                        await vector_store.initialize()

                        collection_name = f"space_{space_id}_chunks"

                        # Ensure collection exists
                        if not await vector_store.collection_exists(collection_name):
                            await vector_store.create_collection(
                                collection_name=collection_name,
                                dimension=len(chunk_embeddings[0]),  # e.g., 3072
                            )

                        # Prepare metadata for vectors
                        vector_metadatas = [
                            VectorMetadata(
                                chunk_id=chunk.id,
                                document_id=document.id,
                                space_id=space_id,
                                chunk_index=chunk.chunk_index,
                                chunk_type=chunk.chunk_type,
                            )
                            for chunk in chunks_to_create
                        ]

                        # Store vectors in Chroma
                        vector_ids = await vector_store.add_vectors(
                            collection_name=collection_name,
                            vectors=chunk_embeddings,
                            metadatas=vector_metadatas,
                        )

                        logger.info(
                            f"Stored {len(vector_ids)} vectors in Chroma collection: {collection_name}"
                        )

                    except Exception as vector_error:
                        logger.error(f"Failed to store vectors in Chroma: {vector_error}")
                        # Don't fail the entire process - vectors can be regenerated
                        document.processing_error = f"Vector storage error: {vector_error!s}"

                    # Step 6: Update document metadata
                    # document.embedding = doc_embedding  # Remove - not storing in SQL
                    document.chunk_count = len(chunks_data)
                    document.indexed_at = datetime.utcnow()

                    await session.commit()

                    logger.info(f"Vectorization completed for document {document.id}")
                else:
                    logger.warning(f"No chunks created for document {document.id}")

            except Exception as e:
                logger.error(f"Vectorization failed for document {document.id}: {e}")
                # Vectorization failure doesn't fail the entire process
                document.processing_error = f"Vectorization error: {e!s}"
                await session.commit()

            # Trigger entity extraction if enabled
            await _trigger_entity_extraction_if_enabled(session, space_id, document.id)

            await task_logger.log_task_success(
                log_entry,
                f"Successfully processed file: {filename}",
                {
                    "document_id": document.id,
                    "content_length": len(markdown_content),
                    "etl_service": service_used,
                    "chunk_count": document.chunk_count,
                },
            )

        except Exception as e:
            error_message = f"Failed to process file: {filename}"
            await task_logger.log_task_failure(
                log_entry,
                error_message,
                str(e),
                {"error_type": type(e).__name__},
            )
            logger.error(f"{error_message}: {e}")
            raise
        finally:
            # Clean up temp file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {file_path}: {cleanup_error}")


# ============================================================================
# data-construction Document Processing Pipeline
# ============================================================================


@celery_app.task(name="langflow.workers.process_document_pipeline", bind=True)
def process_document_pipeline_task(self, document_id: int):
    """Process document through the complete pipeline:
    1. Download file from data-construction
    2. ETL parsing (Unstructured/LlamaCloud/Docling)
    3. Chunking (RecursiveChunker/CodeChunker)
    4. Embedding generation
    5. Save to database
    6. Knowledge graph extraction (Phase 4)

    This task is triggered after document upload to data-construction.
    """
    import asyncio

    logger.info(f"Starting document processing pipeline for document_id={document_id}")

    async def _process_document():
        """Async processing function."""
        session_maker = get_celery_session_maker()
        async with session_maker() as session:
            try:
                # Run complete ETL pipeline
                from langflow.services.etl.pipeline import process_document_etl_pipeline

                await process_document_etl_pipeline(document_id, session)

                logger.info(f"Document {document_id} processing completed successfully")

            except Exception as e:
                logger.error(f"Document processing pipeline failed for document_id={document_id}: {e}")
                raise

    # Run async function in event loop
    asyncio.run(_process_document())
    logger.info(f"Document processing pipeline completed for document_id={document_id}")
