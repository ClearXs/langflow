"""RerankerService for search result reranking in Holo knowledge system."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rerankers import Document as RerankerDocument

from langflow.services.base import Service

if TYPE_CHECKING:
    from langflow.services.settings.service import SettingsService

logger = logging.getLogger(__name__)


class RerankerService(Service):
    """Service for reranking documents using a configured reranker.

    This service provides:
    - Document reranking using various reranker models
    - Support for document-grouped format (with chunks)
    - Support for chunk-based format (legacy)
    - Fallback to original order on errors
    """

    name = "reranker_service"

    def __init__(self, settings_service: SettingsService):
        """Initialize RerankerService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()

    def rerank_documents(
        self, query_text: str, documents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Rerank documents using the configured reranker.

        Documents can be either:
        - Document-grouped (new format): Has `document_id`, `chunks` list, and `content` (concatenated)
        - Chunk-based (legacy format): Individual chunks with `chunk_id` and `content`

        Args:
            query_text: The query text to use for reranking
            documents: List of document dictionaries to rerank

        Returns:
            Reranked documents with preserved structure
        """
        # Get reranker instance from settings
        reranker_instance = self.settings.reranker_instance

        if not reranker_instance or not documents:
            return documents

        try:
            # Create Document objects for the rerankers library
            reranker_docs = []
            for i, doc in enumerate(documents):
                # Use document_id for matching
                doc_id = doc.get("document_id") or f"doc_{i}"
                # Use concatenated content for reranking
                content = doc.get("content", "")
                score = doc.get("score", 0.0)
                document_info = doc.get("document", {})

                reranker_docs.append(
                    RerankerDocument(
                        text=content,
                        doc_id=doc_id,
                        metadata={
                            "document_id": document_info.get("id", ""),
                            "document_title": document_info.get("title", ""),
                            "document_type": document_info.get("document_type", ""),
                            "rrf_score": score,
                            # Track original index for fallback matching
                            "original_index": i,
                        },
                    )
                )

            # Rerank using the configured reranker
            reranking_results = reranker_instance.rank(query=query_text, docs=reranker_docs)

            # Process the results from the reranker
            # Convert to serializable dictionaries while preserving full structure
            serialized_results = []
            for result in reranking_results.results:
                result_doc_id = result.document.doc_id
                original_index = result.document.metadata.get("original_index")

                # Find the original document by document_id
                original_doc = None
                for doc in documents:
                    if doc.get("document_id") == result_doc_id:
                        original_doc = doc
                        break

                # Fallback to original index if ID matching fails
                if (
                    original_doc is None
                    and original_index is not None
                    and 0 <= original_index < len(documents)
                ):
                    original_doc = documents[original_index]

                if original_doc:
                    # Create a deep copy to preserve the full structure including chunks
                    reranked_doc = original_doc.copy()
                    # Preserve chunks list if present (important for citation formatting)
                    if "chunks" in original_doc:
                        reranked_doc["chunks"] = original_doc["chunks"]
                    reranked_doc["score"] = float(result.score)
                    reranked_doc["rank"] = result.rank
                    serialized_results.append(reranked_doc)

            logger.info(f"Reranked {len(serialized_results)} documents for query: {query_text[:50]}")
            return serialized_results

        except Exception as e:
            # Log the error
            logger.error(f"Error during reranking: {e!s}")
            # Fall back to original documents without reranking
            return documents

    def is_enabled(self) -> bool:
        """Check if reranking is enabled.

        Returns:
            True if reranking is enabled and reranker instance exists
        """
        return self.settings.rerankers_enabled and self.settings.reranker_instance is not None
