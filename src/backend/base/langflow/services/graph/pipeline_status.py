"""Helpers for knowledge graph pipeline status and incremental rebuilds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langflow.utils import generate_content_hash


def compute_graph_content_hash(document, space_id: int) -> str | None:
    """Return the content hash used for graph extraction checks."""
    if getattr(document, "content_hash", None):
        return document.content_hash
    content = getattr(document, "content", None)
    if content:
        return generate_content_hash(content, space_id)
    return None


def should_skip_graph_extraction(
    document,
    space_id: int,
) -> tuple[bool, str | None, str | None]:
    """Decide if graph extraction can be skipped based on content hash."""
    current_hash = compute_graph_content_hash(document, space_id)
    metadata = getattr(document, "document_metadata", None) or {}
    stored_hash = metadata.get("graph_content_hash")

    if document.graph_extracted and not document.content_needs_reindexing:
        if stored_hash and current_hash and stored_hash == current_hash:
            return True, "no_change", current_hash
        if not stored_hash and current_hash:
            return True, "backfill_hash", current_hash

    return False, None, current_hash


def apply_graph_status(
    document,
    status: str,
    *,
    error: str | None = None,
    content_hash: str | None = None,
    skip_reason: str | None = None,
    retry_count: int | None = None,
) -> None:
    """Update graph pipeline status metadata on a document."""
    metadata: dict[str, Any] = dict(getattr(document, "document_metadata", None) or {})
    metadata["graph_status"] = status
    metadata["graph_updated_at"] = datetime.now(timezone.utc).isoformat()

    if content_hash is not None:
        metadata["graph_content_hash"] = content_hash

    if error:
        metadata["graph_error"] = str(error)
    else:
        metadata.pop("graph_error", None)

    if skip_reason:
        metadata["graph_skip_reason"] = skip_reason
    else:
        metadata.pop("graph_skip_reason", None)

    if retry_count is not None:
        metadata["graph_retry_count"] = retry_count

    document.document_metadata = metadata
