"""Complete ETL pipeline for document processing.

This pipeline coordinates:
1. File download from data-construction
2. ETL parsing (Unstructured/LlamaCloud/Docling)
3. Chunking (RecursiveChunker/CodeChunker)
4. Embedding generation
5. Database storage
6. Knowledge graph extraction (Phase 4 - placeholder)
"""

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


async def download_file_to_temp(file_id: int) -> tuple[str, str]:
    """Download file from data-construction to temporary location.

    Args:
        file_id: File ID in data-construction

    Returns:
        Tuple of (temp_path, filename)
    """
    from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
    from lfx.services.feign.service import get_feign_service

    feign_service = get_feign_service()
    dc_client = DataConstructionFeignClient(feign_service)

    # Download file
    content, filename = await dc_client.download_file(file_id)

    # Save to temp file
    suffix = Path(filename).suffix
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        prefix=f"lfx_feign_{file_id}_"
    )
    temp_path = temp_file.name
    temp_file.close()  # Close so we can write with aiofiles

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(content)

    logger.info(f"Downloaded file to {temp_path}")
    return temp_path, filename


async def process_document_etl_pipeline(
    document_id: int,
    session
):
    """Process document through complete ETL pipeline.

    Args:
        document_id: Document ID to process
        session: Database session

    This function implements the complete flow:
    1. Download file from data-construction
    2. Parse with ETL service
    3. Chunk content
    4. Generate embeddings
    5. Save chunks to database
    6. Trigger knowledge graph extraction (Phase 4)

    Raises:
        Exception: If any step fails
    """
    from sqlmodel import select

    from langflow.services.database.models.chunk import Chunk
    from langflow.services.database.models.document import Document
    from langflow.services.etl.chunking import get_chunking_service
    from langflow.services.etl.embeddings import get_embedding_service
    from langflow.services.etl.processors import process_document_with_fallback

    # Get document
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise ValueError(f"Document {document_id} not found")

    logger.info(f"Processing document: {document.title} (ID: {document.id})")

    # Update status
    document.processing_status = "processing"
    await session.commit()

    temp_path = None

    try:
        # Step 1: Download file from data-construction
        logger.info("Step 1: Downloading file from data-construction")
        temp_path, filename = await download_file_to_temp(
            document.data_construction_file_id
        )

        # Step 2: ETL parsing
        logger.info("Step 2: Parsing document with ETL service")
        markdown_content, etl_service_used = await process_document_with_fallback(temp_path)

        # Update document with parsed content
        document.content = markdown_content[:50000]  # Limit to first 50k chars
        document.token_count = len(markdown_content.split())
        document.etl_service = etl_service_used

        logger.info(
            f"Parsed document: {len(markdown_content)} chars, "
            f"{document.token_count} tokens using {etl_service_used}"
        )

        # Step 3: Chunking
        logger.info("Step 3: Chunking document")
        chunking_service = get_chunking_service()
        chunks_data = await chunking_service.chunk_document(
            content=markdown_content,
            file_type=document.file_type,
            file_name=document.file_name
        )

        document.chunk_count = len(chunks_data)
        logger.info(f"Created {len(chunks_data)} chunks")

        # Step 4: Generate embeddings
        logger.info("Step 4: Generating embeddings")
        embedding_service = get_embedding_service()

        # Document-level embedding (use first 5000 chars)
        doc_preview = markdown_content[:5000]
        doc_embedding = await embedding_service.embed_text(doc_preview)
        document.embedding = doc_embedding

        # Chunk-level embeddings (batch processing)
        chunk_texts = [chunk["content"] for chunk in chunks_data]
        chunk_embeddings = await embedding_service.embed_batch(chunk_texts)

        logger.info(f"Generated {len(chunk_embeddings)} chunk embeddings")

        # Step 5: Save chunks to database
        logger.info("Step 5: Saving chunks to database")

        for chunk_data, embedding in zip(chunks_data, chunk_embeddings):
            chunk = Chunk(
                content=chunk_data["content"],
                embedding=embedding,
                chunk_index=chunk_data["index"],
                token_count=chunk_data["token_count"],
                chunk_type=chunk_data["type"],
                programming_language=chunk_data.get("language"),
                document_id=document.id,
                space_id=document.space_id
            )
            session.add(chunk)

        # Step 6: Knowledge graph extraction
        logger.info("Step 6: Extracting knowledge graph")

        try:
            from langflow.services.graph import get_graph_service
            from langflow.services.graph.binding_sync import (
                index_entities_in_vector_store,
                sync_graph_bindings_from_neo4j,
            )

            graph_service = get_graph_service()
            graph_stats = await graph_service.extract_graph_from_document(
                document_id=document.id,
                content=markdown_content,
                space_id=document.space_id,
                title=document.title
            )

            if graph_stats["success"]:
                updated_entities = await sync_graph_bindings_from_neo4j(
                    session,
                    space_id=document.space_id,
                    document_id=document.id,
                )
                await index_entities_in_vector_store(updated_entities)
                document.graph_extracted = True
                document.entity_count = graph_stats["entity_count"]
                document.relation_count = graph_stats["relation_count"]

                logger.info(
                    f"Knowledge graph extracted: {graph_stats['entity_count']} entities, "
                    f"{graph_stats['relation_count']} relations"
                )
            else:
                logger.warning(f"Knowledge graph extraction failed: {graph_stats.get('error')}")
                document.graph_extracted = False

        except Exception as e:
            logger.error(f"Knowledge graph extraction error: {e}")
            document.graph_extracted = False

        # Step 7: Mark as completed
        document.processing_status = "completed"
        document.indexed_at = datetime.utcnow()
        await session.commit()

        logger.info(f"Document {document_id} processed successfully")

        return document

    except Exception as e:
        logger.error(f"ETL pipeline failed for document {document_id}: {e}")

        # Update document with error
        document.processing_status = "failed"
        document.processing_error = str(e)
        await session.commit()

        raise

    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temp file: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
