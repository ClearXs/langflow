# Force asyncio to use standard event loop before unstructured imports
import asyncio

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.schema import (
    DocumentsCreate,
    DocumentWithChunksRead,
    PaginatedResponse,
)
from langflow.services.database.models.chunk import Chunk
from langflow.services.database.models.document import (
    Document,
    DocumentRead,
    DocumentType,
    DocumentUpdate,
)
from langflow.services.database.models.role import Permission
from langflow.services.database.models.space import Space
from langflow.services.database.models.space_membership import SpaceMembership
from langflow.utils.rbac import check_permission

try:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except RuntimeError as e:
    print("Error setting event loop policy", e)

import os

os.environ["UNSTRUCTURED_HAS_PATCHED_LOOP"] = "1"


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/")
async def create_documents(
    request: DocumentsCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Create new documents.
    Requires DOCUMENTS_CREATE permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            request.search_space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You don't have permission to create documents in this search space",
        )

        if request.document_type == DocumentType.EXTENSION:
            from langflow.workers.document_tasks import (
                process_extension_document_task,
            )

            for individual_document in request.content:
                # Convert document to dict for Celery serialization
                document_dict = {
                    "metadata": {
                        "VisitedWebPageTitle": individual_document.metadata.VisitedWebPageTitle,
                        "VisitedWebPageURL": individual_document.metadata.VisitedWebPageURL,
                        "BrowsingSessionId": individual_document.metadata.BrowsingSessionId,
                        "VisitedWebPageDateWithTimeInISOString": individual_document.metadata.VisitedWebPageDateWithTimeInISOString,
                        "VisitedWebPageVisitDurationInMilliseconds": individual_document.metadata.VisitedWebPageVisitDurationInMilliseconds,
                        "VisitedWebPageReffererURL": individual_document.metadata.VisitedWebPageReffererURL,
                    },
                    "pageContent": individual_document.pageContent,
                }
                process_extension_document_task.delay(
                    document_dict, request.search_space_id, str(current_user.id)
                )
        elif request.document_type == DocumentType.YOUTUBE_VIDEO:
            from langflow.workers.document_tasks import process_youtube_video_task

            for url in request.content:
                process_youtube_video_task.delay(
                    url, request.search_space_id, str(current_user.id)
                )
        else:
            raise HTTPException(status_code=400, detail="Invalid document type")

        await db.commit()
        return {"message": "Documents processed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to process documents: {e!s}"
        ) from e


@router.post("/fileupload")
async def create_documents_file_upload(
    files: list[UploadFile],
    search_space_id: int = Form(...),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Upload files as documents.
    Requires DOCUMENTS_CREATE permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You don't have permission to create documents in this search space",
        )

        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        for file in files:
            try:
                # Save file to a temporary location to avoid stream issues
                import os
                import tempfile

                # Create temp file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(file.filename)[1]
                ) as temp_file:
                    temp_path = temp_file.name

                # Write uploaded file to temp file
                content = await file.read()
                with open(temp_path, "wb") as f:
                    f.write(content)

                from langflow.workers.document_tasks import (
                    process_file_upload_task,
                )

                process_file_upload_task.delay(
                    temp_path, file.filename, search_space_id, str(current_user.id)
                )
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to process file {file.filename}: {e!s}",
                ) from e

        await db.commit()
        return {"message": "Files uploaded for processing"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to upload files: {e!s}"
        ) from e


@router.get("/", response_model=PaginatedResponse[DocumentRead])
async def read_documents(
    skip: int | None = None,
    page: int | None = None,
    page_size: int = 50,
    search_space_id: str | None = None,
    document_types: str | None = None,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """List documents the user has access to, with optional filtering and pagination.
    Requires DOCUMENTS_READ permission for the search space(s).

    Args:
        skip: Absolute number of items to skip from the beginning. If provided, it takes precedence over 'page'.
        page: Zero-based page index used when 'skip' is not provided.
        page_size: Number of items per page (default: 50). Use -1 to return all remaining items after the offset.
        search_space_id: If provided, restrict results to a specific search space.
        document_types: Comma-separated list of document types to filter by (e.g., "EXTENSION,FILE,SLACK_CONNECTOR").
        session: Database session (injected).
        user: Current authenticated user (injected).

    Returns:
        PaginatedResponse[DocumentRead]: Paginated list of documents visible to the user.

    Notes:
        - If both 'skip' and 'page' are provided, 'skip' is used.
        - Results are scoped to documents in search spaces the user has membership in.
    """
    try:
        from sqlalchemy import func

        # Convert search_space_id from string to int, handling "undefined" and empty strings
        parsed_search_space_id = None
        if search_space_id is not None and search_space_id.strip() and search_space_id.lower() != "undefined":
            try:
                parsed_search_space_id = int(search_space_id)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid search_space_id: must be an integer, got '{search_space_id}'",
                )

        # If specific search_space_id, check permission
        if parsed_search_space_id is not None:
            await check_permission(
                db,
                current_user,
                parsed_search_space_id,
                Permission.DOCUMENTS_READ.value,
                "You don't have permission to read documents in this search space",
            )
            query = select(Document).filter(Document.space_id == parsed_search_space_id)
            count_query = (
                select(func.count())
                .select_from(Document)
                .filter(Document.space_id == parsed_search_space_id)
            )
        else:
            # Get documents from all search spaces user has membership in
            query = (
                select(Document)
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
            )
            count_query = (
                select(func.count())
                .select_from(Document)
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
            )

        # Filter by document_types if provided
        if document_types is not None and document_types.strip():
            type_list = [t.strip() for t in document_types.split(",") if t.strip()]
            if type_list:
                query = query.filter(Document.document_type.in_(type_list))
                count_query = count_query.filter(Document.document_type.in_(type_list))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Calculate offset
        offset = 0
        if skip is not None:
            offset = skip
        elif page is not None:
            offset = page * page_size

        # Get paginated results
        if page_size == -1:
            result = await db.execute(query.offset(offset))
        else:
            result = await db.execute(query.offset(offset).limit(page_size))

        db_documents = result.scalars().all()

        # Convert database objects to API-friendly format
        api_documents = []
        for doc in db_documents:
            api_documents.append(
                DocumentRead(
                    id=doc.id,
                    connector_id=doc.connector_id,
                    space_id=doc.space_id,
                    user_id=doc.user_id,
                    title=doc.title,
                    content=doc.content,
                    url=doc.url,
                    doc_type=doc.doc_type,
                    blocknote_document=doc.blocknote_document,
                    embedding=doc.embedding,
                    content_hash=doc.content_hash,
                    unique_identifier_hash=doc.unique_identifier_hash,
                    content_needs_reindexing=doc.content_needs_reindexing,
                    document_metadata=doc.document_metadata,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    data_construction_file_id=doc.data_construction_file_id,
                    data_construction_folder_id=doc.data_construction_folder_id,
                    etl_service=doc.etl_service,
                    chunk_count=doc.chunk_count,
                    token_count=doc.token_count,
                    processing_status=doc.processing_status,
                    processing_error=doc.processing_error,
                    graph_extracted=doc.graph_extracted,
                    entity_count=doc.entity_count,
                    relation_count=doc.relation_count,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                    indexed_at=doc.indexed_at,
                )
            )

        # Calculate pagination info
        actual_page = (
            page if page is not None else (offset // page_size if page_size > 0 else 0)
        )
        has_more = (offset + len(api_documents)) < total if page_size > 0 else False

        return PaginatedResponse(
            items=api_documents,
            total=total,
            page=actual_page,
            page_size=page_size,
            has_more=has_more,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch documents: {e!s}"
        ) from e


@router.get("/search", response_model=PaginatedResponse[DocumentRead])
async def search_documents(
    title: str,
    skip: int | None = None,
    page: int | None = None,
    page_size: int = 50,
    search_space_id: int | None = None,
    document_types: str | None = None,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Search documents by title substring, optionally filtered by search_space_id and document_types.
    Requires DOCUMENTS_READ permission for the search space(s).

    Args:
        title: Case-insensitive substring to match against document titles. Required.
        skip: Absolute number of items to skip from the beginning. If provided, it takes precedence over 'page'. Default: None.
        page: Zero-based page index used when 'skip' is not provided. Default: None.
        page_size: Number of items per page. Use -1 to return all remaining items after the offset. Default: 50.
        search_space_id: Filter results to a specific search space. Default: None.
        document_types: Comma-separated list of document types to filter by (e.g., "EXTENSION,FILE,SLACK_CONNECTOR").
        session: Database session (injected).
        user: Current authenticated user (injected).

    Returns:
        PaginatedResponse[DocumentRead]: Paginated list of documents matching the query and filter.

    Notes:
        - Title matching uses ILIKE (case-insensitive).
        - If both 'skip' and 'page' are provided, 'skip' is used.
    """
    try:
        from sqlalchemy import func

        # If specific search_space_id, check permission
        if search_space_id is not None:
            await check_permission(
                db,
                current_user,
                search_space_id,
                Permission.DOCUMENTS_READ.value,
                "You don't have permission to read documents in this search space",
            )
            query = select(Document).filter(Document.space_id == search_space_id)
            count_query = (
                select(func.count())
                .select_from(Document)
                .filter(Document.space_id == search_space_id)
            )
        else:
            # Get documents from all search spaces user has membership in
            query = (
                select(Document)
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
            )
            count_query = (
                select(func.count())
                .select_from(Document)
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
            )

        # Only search by title (case-insensitive)
        query = query.filter(Document.title.ilike(f"%{title}%"))
        count_query = count_query.filter(Document.title.ilike(f"%{title}%"))

        # Filter by document_types if provided
        if document_types is not None and document_types.strip():
            type_list = [t.strip() for t in document_types.split(",") if t.strip()]
            if type_list:
                query = query.filter(Document.document_type.in_(type_list))
                count_query = count_query.filter(Document.document_type.in_(type_list))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Calculate offset
        offset = 0
        if skip is not None:
            offset = skip
        elif page is not None:
            offset = page * page_size

        # Get paginated results
        if page_size == -1:
            result = await db.execute(query.offset(offset))
        else:
            result = await db.execute(query.offset(offset).limit(page_size))

        db_documents = result.scalars().all()

        # Convert database objects to API-friendly format
        api_documents = []
        for doc in db_documents:
            api_documents.append(
                DocumentRead(
                    id=doc.id,
                    connector_id=doc.connector_id,
                    space_id=doc.space_id,
                    user_id=doc.user_id,
                    title=doc.title,
                    content=doc.content,
                    url=doc.url,
                    doc_type=doc.doc_type,
                    blocknote_document=doc.blocknote_document,
                    embedding=doc.embedding,
                    content_hash=doc.content_hash,
                    unique_identifier_hash=doc.unique_identifier_hash,
                    content_needs_reindexing=doc.content_needs_reindexing,
                    document_metadata=doc.document_metadata,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    data_construction_file_id=doc.data_construction_file_id,
                    data_construction_folder_id=doc.data_construction_folder_id,
                    etl_service=doc.etl_service,
                    chunk_count=doc.chunk_count,
                    token_count=doc.token_count,
                    processing_status=doc.processing_status,
                    processing_error=doc.processing_error,
                    graph_extracted=doc.graph_extracted,
                    entity_count=doc.entity_count,
                    relation_count=doc.relation_count,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                    indexed_at=doc.indexed_at,
                )
            )

        # Calculate pagination info
        actual_page = (
            page if page is not None else (offset // page_size if page_size > 0 else 0)
        )
        has_more = (offset + len(api_documents)) < total if page_size > 0 else False

        return PaginatedResponse(
            items=api_documents,
            total=total,
            page=actual_page,
            page_size=page_size,
            has_more=has_more,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search documents: {e!s}"
        ) from e


@router.get("/type-counts")
async def get_document_type_counts(
    search_space_id: int | None = None,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get counts of documents by type for search spaces the user has access to.
    Requires DOCUMENTS_READ permission for the search space(s).

    Args:
        search_space_id: If provided, restrict counts to a specific search space.
        session: Database session (injected).
        user: Current authenticated user (injected).

    Returns:
        Dict mapping document types to their counts.
    """
    try:
        from sqlalchemy import func

        if search_space_id is not None:
            # Check permission for specific search space
            await check_permission(
                db,
                current_user,
                search_space_id,
                Permission.DOCUMENTS_READ.value,
                "You don't have permission to read documents in this search space",
            )
            query = (
                select(Document.doc_type, func.count(Document.id))
                .filter(Document.space_id == search_space_id)
                .group_by(Document.doc_type)
            )
        else:
            # Get counts from all search spaces user has membership in
            query = (
                select(Document.doc_type, func.count(Document.id))
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
                .group_by(Document.doc_type)
            )

        result = await db.execute(query)
        type_counts = dict(result.all())

        return type_counts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch document type counts: {e!s}"
        ) from e


@router.get("/by-chunk/{chunk_id}", response_model=DocumentWithChunksRead)
async def get_document_by_chunk_id(
    chunk_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Retrieves a document based on a chunk ID, including all its chunks ordered by creation time.
    Requires DOCUMENTS_READ permission for the search space.
    The document's embedding and chunk embeddings are excluded from the response.
    """
    try:
        # First, get the chunk and verify it exists
        chunk_result = await db.execute(select(Chunk).filter(Chunk.id == chunk_id))
        chunk = chunk_result.scalars().first()

        if not chunk:
            raise HTTPException(
                status_code=404, detail=f"Chunk with id {chunk_id} not found"
            )

        # Get the associated document
        document_result = await db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .filter(Document.id == chunk.document_id)
        )
        document = document_result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            document.search_space_id,
            Permission.DOCUMENTS_READ.value,
            "You don't have permission to read documents in this search space",
        )

        # Sort chunks by creation time
        sorted_chunks = sorted(document.chunks, key=lambda x: x.created_at)

        # Return the document with its chunks
        return DocumentWithChunksRead(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            document_metadata=document.document_metadata,
            content=document.content,
            content_hash=document.content_hash,
            unique_identifier_hash=document.unique_identifier_hash,
            created_at=document.created_at,
            updated_at=document.updated_at,
            search_space_id=document.search_space_id,
            chunks=sorted_chunks,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve document: {e!s}"
        ) from e


@router.get("/{document_id}", response_model=DocumentRead)
async def read_document(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get a specific document by ID.
    Requires DOCUMENTS_READ permission for the search space.
    """
    try:
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404, detail=f"Document with id {document_id} not found"
            )

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            document.search_space_id,
            Permission.DOCUMENTS_READ.value,
            "You don't have permission to read documents in this search space",
        )

        # Convert database object to API-friendly format
        return DocumentRead(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            document_metadata=document.document_metadata,
            content=document.content,
            content_hash=document.content_hash,
            unique_identifier_hash=document.unique_identifier_hash,
            created_at=document.created_at,
            updated_at=document.updated_at,
            search_space_id=document.search_space_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch document: {e!s}"
        ) from e


@router.put("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update a document.
    Requires DOCUMENTS_UPDATE permission for the search space.
    """
    try:
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        db_document = result.scalars().first()

        if not db_document:
            raise HTTPException(
                status_code=404, detail=f"Document with id {document_id} not found"
            )

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            db_document.search_space_id,
            Permission.DOCUMENTS_UPDATE.value,
            "You don't have permission to update documents in this search space",
        )

        update_data = document_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_document, key, value)
        await db.commit()
        await db.refresh(db_document)

        # Convert to DocumentRead for response
        return DocumentRead(
            id=db_document.id,
            title=db_document.title,
            document_type=db_document.document_type,
            document_metadata=db_document.document_metadata,
            content=db_document.content,
            content_hash=db_document.content_hash,
            unique_identifier_hash=db_document.unique_identifier_hash,
            created_at=db_document.created_at,
            updated_at=db_document.updated_at,
            search_space_id=db_document.search_space_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update document: {e!s}"
        ) from e


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete a document.
    Requires DOCUMENTS_DELETE permission for the search space.
    """
    try:
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404, detail=f"Document with id {document_id} not found"
            )

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            document.space_id,
            Permission.DOCUMENTS_DELETE.value,
            "You don't have permission to delete documents in this search space",
        )

        # Delete knowledge graph data if exists
        if document.graph_extracted:
            try:
                from langflow.services.graph import get_graph_service

                graph_service = get_graph_service()
                await graph_service.delete_document_graph(
                    document_id=document.id,
                    space_id=document.space_id
                )
            except Exception as e:
                logger.warning(f"Failed to delete graph data for document {document_id}: {e}")

        await db.delete(document)
        await db.commit()
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {e!s}"
        ) from e


# ============================================================================
# data-construction Integration Endpoints
# ============================================================================


@router.post("/upload-to-data-construction")
async def upload_document_to_data_construction(
    file: UploadFile,
    folder_id: int = Form(...),
    space_id: int = Form(...),
    connector_id: int | None = Form(None),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Upload a document to data-construction microservice and create a document record.

    This endpoint:
    1. Uploads the file to data-construction service
    2. Creates a Document record with status='pending'
    3. Triggers background processing (vectorization + graph extraction)

    Requires DOCUMENTS_CREATE permission.
    """
    import hashlib
    from pathlib import Path

    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You don't have permission to create documents in this space",
        )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(file_content).hexdigest()

        # Check if document already exists
        result = await db.execute(
            select(Document).filter(
                Document.content_hash == content_hash,
                Document.space_id == space_id
            )
        )
        existing_doc = result.scalars().first()

        if existing_doc:
            return {
                "message": "Document already exists",
                "document_id": existing_doc.id,
                "duplicate": True
            }

        # Upload to data-construction
        from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
        from lfx.services.feign.service import get_feign_service

        feign_service = get_feign_service()
        dc_client = DataConstructionFeignClient(feign_service)

        # Upload file
        dc_file = await dc_client.upload_file(
            folder_id=folder_id,
            file_content=file_content,
            filename=file.filename
        )

        # Generate unique identifier hash
        unique_id_hash = hashlib.sha256(
            f"{space_id}_{dc_file['id']}_{file.filename}".encode()
        ).hexdigest()

        # Create Document record
        document = Document(
            connector_id=connector_id or 1,  # Default connector if not provided
            space_id=space_id,
            user_id=current_user.id,
            title=file.filename,
            content="",  # Will be populated during processing
            url=None,
            doc_type="PDF" if file.filename.lower().endswith(".pdf") else "FILE",
            content_hash=content_hash,
            unique_identifier_hash=unique_id_hash,
            file_name=file.filename,
            file_type=Path(file.filename).suffix.lstrip("."),
            file_size=file_size,
            data_construction_file_id=dc_file["id"],
            data_construction_folder_id=folder_id,
            processing_status="pending"
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Trigger background processing
        from langflow.workers.document_tasks import process_document_pipeline_task

        process_document_pipeline_task.delay(document.id)

        return {
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "status": "pending",
            "data_construction_file_id": dc_file["id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {e!s}"
        ) from e


@router.get("/{document_id}/editor-content")
async def get_document_editor_content(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get document content in BlockNote JSON format for editor.

    If blocknote_document is null, performs lazy migration from content field.

    Requires DOCUMENTS_READ permission.
    """
    from datetime import datetime

    try:
        # Get document
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )

        # Check permission
        await check_permission(
            db,
            current_user,
            document.space_id,
            Permission.DOCUMENTS_READ.value,
            "You don't have permission to read documents in this space",
        )

        # Check if BlockNote JSON exists
        if document.blocknote_document and document.blocknote_document != "null":
            import json
            try:
                blocknote_content = (
                    json.loads(document.blocknote_document)
                    if isinstance(document.blocknote_document, str)
                    else document.blocknote_document
                )
            except (json.JSONDecodeError, TypeError):
                blocknote_content = []

            return {
                "document_id": document.id,
                "title": document.title,
                "blocknote_content": blocknote_content,
                "doc_type": document.doc_type,
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            }

        # Lazy migration: Convert content to BlockNote JSON
        blocknote_json = await _convert_content_to_blocknote(document.content or "")

        # Save migrated content to database
        import json
        document.blocknote_document = json.dumps(blocknote_json)
        document.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(document)

        return {
            "document_id": document.id,
            "title": document.title,
            "blocknote_content": blocknote_json,
            "doc_type": document.doc_type,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get editor content: {e!s}"
        ) from e


async def _convert_content_to_blocknote(content: str) -> list[dict]:
    """Convert plain text/markdown content to BlockNote JSON format.

    BlockNote format:
    [
      {
        "id": "unique-id",
        "type": "paragraph",
        "content": [{"type": "text", "text": "content"}]
      }
    ]
    """
    import uuid

    if not content or not content.strip():
        return []

    # Split content by double newlines (paragraphs)
    paragraphs = content.split("\n\n")

    blocks = []
    for idx, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # Detect block type
        block_type = "paragraph"
        block_props = {}
        text = para

        # Check for headings
        if para.startswith("# "):
            block_type = "heading"
            block_props["level"] = 1
            text = para[2:]
        elif para.startswith("## "):
            block_type = "heading"
            block_props["level"] = 2
            text = para[3:]
        elif para.startswith("### "):
            block_type = "heading"
            block_props["level"] = 3
            text = para[4:]
        # Check for list items
        elif para.startswith("- ") or para.startswith("* "):
            block_type = "bulletListItem"
            text = para[2:]
        elif para.startswith("```"):
            block_type = "codeBlock"
            text = para.strip("`").strip()

        # Create block with proper StyledText format
        block = {
            "id": str(uuid.uuid4()),
            "type": block_type,
            "props": block_props if block_props else {},
            "content": [{"type": "text", "text": text, "styles": {}}],
            "children": []
        }

        blocks.append(block)

    return blocks if blocks else [
        {
            "id": str(uuid.uuid4()),
            "type": "paragraph",
            "props": {},
            "content": [{"type": "text", "text": content, "styles": {}}],
            "children": []
        }
    ]


@router.post("/{document_id}/save")
async def save_document_content(
    document_id: int,
    blocknote_content: list[dict],
    title: str | None = None,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Save edited document content in BlockNote JSON format.

    Requires DOCUMENTS_UPDATE permission.
    """
    import json
    from datetime import datetime

    try:
        # Get document
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )

        # Check permission
        await check_permission(
            db,
            current_user,
            document.space_id,
            Permission.DOCUMENTS_UPDATE.value,
            "You don't have permission to update documents in this space",
        )

        # Update document
        document.blocknote_document = json.dumps(blocknote_content)
        if title:
            document.title = title
        document.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(document)

        return {
            "success": True,
            "document_id": document.id,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save document: {e!s}"
        ) from e


@router.get("/{document_id}/download")
async def download_document_from_data_construction(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Download document original file from data-construction service.

    Requires DOCUMENTS_READ permission.
    """
    from fastapi.responses import Response

    try:
        # Get document
        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )

        # Check permission
        await check_permission(
            db,
            current_user,
            document.space_id,
            Permission.DOCUMENTS_READ.value,
            "You don't have permission to read documents in this space",
        )

        # Check if document has data_construction_file_id
        if not document.data_construction_file_id:
            raise HTTPException(
                status_code=400,
                detail="Document was not uploaded via data-construction"
            )

        # Download from data-construction
        from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
        from lfx.services.feign.service import get_feign_service

        feign_service = get_feign_service()
        dc_client = DataConstructionFeignClient(feign_service)

        content, filename = await dc_client.download_file(
            document.data_construction_file_id
        )

        # Return file as download
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download document: {e!s}"
        ) from e


@router.get("/type-counts")
async def get_document_type_counts(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
) -> dict[str, int]:
    """Get document type counts for a space.
    Returns a dictionary mapping document types to their counts.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.DOCUMENTS_READ.value,
            "You don't have permission to read documents in this search space",
        )

        from sqlalchemy import func, select

        # Build query to count documents by type
        stmt = (
            select(
                Document.doc_type,
                func.count(Document.id).label("count")
            )
            .where(Document.space_id == search_space_id)
            .group_by(Document.doc_type)
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Convert to dictionary
        type_counts = {row.doc_type: row.count for row in rows}

        return type_counts

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document type counts: {e!s}"
        ) from e


# ============================================================================
# YouTube Video Processing Endpoint
# ============================================================================


@router.post("/youtube")
async def add_youtube_video(
    video_url: str = Form(...),
    space_id: int = Form(...),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Add a YouTube video by URL. Extracts video ID, transcript, and metadata.

    This endpoint:
    1. Validates YouTube URL and extracts video ID
    2. Creates a Document record with type=YOUTUBE_VIDEO
    3. Triggers background processing to:
       - Extract transcript/captions using YouTube API
       - Extract video metadata (title, description, duration)
       - Vectorize content
       - Extract knowledge graph

    Requires DOCUMENTS_CREATE permission.
    """
    import hashlib
    import re

    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You don't have permission to create documents in this space",
        )

        # Extract video ID from URL
        video_id = None
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)",
            r"youtube\.com\/embed\/([^&\n?#]+)",
            r"youtube\.com\/v\/([^&\n?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                video_id = match.group(1)
                break

        if not video_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid YouTube URL. Please provide a valid YouTube video link."
            )

        # Generate unique identifier hash (space_id + video_id)
        unique_id_hash = hashlib.sha256(
            f"{space_id}_youtube_{video_id}".encode()
        ).hexdigest()

        # Check if video already exists in this space
        result = await db.execute(
            select(Document).filter(
                Document.unique_identifier_hash == unique_id_hash,
                Document.space_id == space_id
            )
        )
        existing_doc = result.scalars().first()

        if existing_doc:
            return {
                "message": "YouTube video already exists in this space",
                "document_id": existing_doc.id,
                "duplicate": True
            }

        # Create Document record (content will be populated by background task)
        document = Document(
            connector_id=1,  # Default connector
            space_id=space_id,
            user_id=current_user.id,
            title=f"YouTube: {video_id}",  # Will be updated with actual title
            content="",  # Will be populated with transcript
            url=video_url,
            doc_type="YOUTUBE",
            content_hash="",  # Will be calculated after transcript extraction
            unique_identifier_hash=unique_id_hash,
            document_metadata={
                "video_id": video_id,
                "video_url": video_url,
                "source": "youtube"
            },
            processing_status="pending"
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Trigger background processing
        from langflow.workers.document_tasks import process_youtube_video_task

        process_youtube_video_task.delay(document.id, video_url, video_id)

        return {
            "message": "YouTube video added successfully",
            "document_id": document.id,
            "video_id": video_id,
            "status": "pending"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add YouTube video: {e!s}"
        ) from e


# ============================================================================
# Web Crawling Endpoint
# ============================================================================


@router.post("/web-crawl")
async def crawl_web_pages(
    urls: list[str] = Form(...),
    crawl_subpages: bool = Form(False),
    max_depth: int = Form(1),
    space_id: int = Form(...),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Crawl web pages and add content to documents.

    This endpoint:
    1. Validates URLs
    2. Creates Document records for each URL with type=WEB_PAGE
    3. Triggers background processing to:
       - Crawl web page content
       - Optionally crawl linked subpages up to max_depth
       - Extract and clean HTML content
       - Vectorize content
       - Extract knowledge graph

    Args:
        urls: List of web page URLs to crawl
        crawl_subpages: Whether to crawl linked pages from the main page
        max_depth: Maximum depth for subpage crawling (1-3)
        space_id: Target space ID

    Requires DOCUMENTS_CREATE permission.
    """
    import hashlib
    from urllib.parse import urlparse

    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You don't have permission to create documents in this space",
        )

        # Validate URLs
        valid_urls = []
        for url in urls:
            url = url.strip()
            if not url:
                continue

            # Basic URL validation
            try:
                parsed = urlparse(url)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    valid_urls.append(url)
            except Exception:
                continue

        if not valid_urls:
            raise HTTPException(
                status_code=400,
                detail="No valid URLs provided"
            )

        # Validate max_depth
        max_depth = max(1, min(3, max_depth))

        created_documents = []

        for url in valid_urls:
            # Generate unique identifier hash (space_id + url)
            unique_id_hash = hashlib.sha256(
                f"{space_id}_webpage_{url}".encode()
            ).hexdigest()

            # Check if URL already exists in this space
            result = await db.execute(
                select(Document).filter(
                    Document.unique_identifier_hash == unique_id_hash,
                    Document.space_id == space_id
                )
            )
            existing_doc = result.scalars().first()

            if existing_doc:
                created_documents.append({
                    "url": url,
                    "document_id": existing_doc.id,
                    "duplicate": True
                })
                continue

            # Create Document record
            document = Document(
                connector_id=1,  # Default connector
                space_id=space_id,
                user_id=current_user.id,
                title=url,  # Will be updated with actual page title
                content="",  # Will be populated with crawled content
                url=url,
                doc_type="WEB_PAGE",
                content_hash="",  # Will be calculated after crawling
                unique_identifier_hash=unique_id_hash,
                document_metadata={
                    "url": url,
                    "crawl_subpages": crawl_subpages,
                    "max_depth": max_depth,
                    "source": "web_crawl"
                },
                processing_status="pending"
            )

            db.add(document)
            await db.flush()
            await db.refresh(document)

            created_documents.append({
                "url": url,
                "document_id": document.id,
                "duplicate": False
            })

            # Trigger background processing
            from langflow.workers.document_tasks import process_web_crawl_task

            process_web_crawl_task.delay(
                document.id,
                url,
                crawl_subpages,
                max_depth
            )

        await db.commit()

        new_count = sum(1 for doc in created_documents if not doc["duplicate"])
        duplicate_count = sum(1 for doc in created_documents if doc["duplicate"])

        return {
            "message": f"Successfully queued {new_count} web pages for crawling",
            "documents": created_documents,
            "new_count": new_count,
            "duplicate_count": duplicate_count
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to crawl web pages: {e!s}"
        ) from e
