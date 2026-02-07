"""Notes routes for creating and managing BlockNote documents.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.schema import PaginatedResponse
from langflow.services.database.models.document import Document, DocumentRead, DocumentType
from langflow.services.database.models.role import Permission
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/notes", tags=["Notes"])


class CreateNoteRequest(BaseModel):
    title: str
    blocknote_document: list[dict[str, Any]] | None = None


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    blocknote_document: list[dict[str, Any]] | None = None


@router.post("/search-spaces/{search_space_id}/notes", response_model=DocumentRead)
async def create_note(
    search_space_id: int,
    request: CreateNoteRequest,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Create a new note (BlockNote document).

    Requires DOCUMENTS_CREATE permission.
    """
    # Check RBAC permission
    await check_permission(
        db,
        current_user,
        search_space_id,
        Permission.DOCUMENTS_CREATE.value,
        "You don't have permission to create notes in this search space",
    )

    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    # Default empty BlockNote structure if not provided
    blocknote_document = request.blocknote_document
    if blocknote_document is None:
        blocknote_document = [
            {
                "type": "paragraph",
                "content": [],
                "children": [],
            }
        ]

    # Generate content hash (use title for now, will be updated on save)
    import hashlib

    content_hash = hashlib.sha256(request.title.encode()).hexdigest()

    # Create document with NOTE type

    document = Document(
        space_id=search_space_id,
        connector_id=1,  # Default connector ID for notes
        user_id=current_user.id,
        title=request.title.strip(),
        doc_type=DocumentType.NOTE,
        content="",  # Empty initially, will be populated on first save/reindex
        content_hash=content_hash,
        unique_identifier_hash=content_hash,  # Use content_hash as unique identifier
        blocknote_document=blocknote_document,
        content_needs_reindexing=False,  # Will be set to True on first save
        document_metadata={"NOTE": True},
        embedding=None,  # Will be generated on first reindex
        updated_at=datetime.now(UTC),
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return DocumentRead.model_validate(document)


@router.get(
    "/search-spaces/{search_space_id}/notes",
    response_model=PaginatedResponse[DocumentRead],
)
async def list_notes(
    search_space_id: int,
    skip: int | None = None,
    page: int | None = None,
    page_size: int = 50,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """List all notes in a search space.

    Requires DOCUMENTS_READ permission.
    """
    # Check RBAC permission
    await check_permission(
        db,
        current_user,
        search_space_id,
        Permission.DOCUMENTS_READ.value,
        "You don't have permission to read notes in this search space",
    )

    from sqlalchemy import func

    # Build query
    query = select(Document).where(
        Document.space_id == search_space_id,
        Document.doc_type == DocumentType.NOTE,
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(Document)
        .where(
            Document.space_id == search_space_id,
            Document.doc_type == DocumentType.NOTE,
        )
        .subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    if skip is not None:
        query = query.offset(skip)
    elif page is not None:
        query = query.offset(page * page_size)
    else:
        query = query.offset(0)

    if page_size > 0:
        query = query.limit(page_size)

    # Order by updated_at descending (most recent first)
    query = query.order_by(Document.updated_at.desc())

    # Execute query
    result = await db.execute(query)
    documents = result.scalars().all()

    # Convert to response models using from_attributes
    items = [DocumentRead.model_validate(doc) for doc in documents]

    # Calculate pagination info
    actual_skip = (
        skip if skip is not None else (page * page_size if page is not None else 0)
    )
    has_more = (actual_skip + len(items)) < total if page_size > 0 else False

    return PaginatedResponse(
        items=items,
        total=total,
        page=page
        if page is not None
        else (actual_skip // page_size if page_size > 0 else 0),
        page_size=page_size,
        has_more=has_more,
    )


@router.delete("/search-spaces/{search_space_id}/notes/{note_id}")
async def delete_note(
    search_space_id: int,
    note_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete a note.

    Requires DOCUMENTS_DELETE permission.
    """
    # Check RBAC permission
    await check_permission(
        db,
        current_user,
        search_space_id,
        Permission.DOCUMENTS_DELETE.value,
        "You don't have permission to delete notes in this search space",
    )

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == note_id,
            Document.space_id == search_space_id,
            Document.doc_type == DocumentType.NOTE,
        )
    )
    document = result.scalars().first()

    if not document:
        raise HTTPException(status_code=404, detail="Note not found")

    # Delete document (chunks will be cascade deleted)
    await db.delete(document)
    await db.commit()

    return {"message": "Note deleted successfully", "note_id": note_id}


@router.put("/search-spaces/{search_space_id}/notes/{note_id}", response_model=DocumentRead)
async def update_note(
    search_space_id: int,
    note_id: int,
    request: UpdateNoteRequest,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update a note.

    Requires DOCUMENTS_UPDATE permission.
    """
    # Check RBAC permission
    await check_permission(
        db,
        current_user,
        search_space_id,
        Permission.DOCUMENTS_UPDATE.value,
        "You don't have permission to update notes in this search space",
    )

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == note_id,
            Document.space_id == search_space_id,
            Document.doc_type == DocumentType.NOTE,
        )
    )
    document = result.scalars().first()

    if not document:
        raise HTTPException(status_code=404, detail="Note not found")

    # Update fields
    if request.title is not None:
        if not request.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        document.title = request.title.strip()

    if request.content is not None:
        document.content = request.content
        # Update content hash
        import hashlib
        document.content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        document.content_needs_reindexing = True

    if request.blocknote_document is not None:
        document.blocknote_document = request.blocknote_document

    document.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(document)

    return DocumentRead.model_validate(document)
