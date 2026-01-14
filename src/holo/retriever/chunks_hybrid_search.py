"""Chunk-level hybrid search retriever for Holo knowledge system.

This module provides hybrid search combining vector similarity and full-text search
for document chunks. Adapted from SurfSense for Langflow integration.

CRITICAL NOTE: Since we removed pgvector dependency, this implementation uses:
- JSON-based embeddings (stored as list[float])
- Cosine similarity calculated in Python instead of PostgreSQL <=> operator
- Full-text search still uses PostgreSQL's to_tsvector/plainto_tsquery
"""

from datetime import datetime
from typing import Any


class ChunksHybridSearchRetriever:
    """Retriever for hybrid search on chunks using vector + full-text search."""

    def __init__(self, db_session):
        """Initialize the hybrid search retriever with a database session.

        Args:
            db_session: SQLAlchemy AsyncSession from FastAPI dependency injection
        """
        self.db_session = db_session

    def _cosine_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        import math

        # Ensure both embeddings have the same length
        if len(embedding1) != len(embedding2):
            return 0.0

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def vector_search(
        self,
        query_text: str,
        top_k: int,
        space_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list:
        """Perform vector similarity search on chunks.

        Args:
            query_text: The search query text
            top_k: Number of results to return
            space_id: The space ID to search within
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of chunks sorted by vector similarity
        """
        from langflow.services.database.models import Chunk, Document

        # Get embedding for the query
        from langflow.services.deps import get_settings
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        settings = get_settings()
        embedding_model = settings.embedding_model_instance
        query_embedding = embedding_model.embed(query_text)

        # Build the query filtered by space
        query = (
            select(Chunk)
            .options(joinedload(Chunk.document).joinedload(Document.space))
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.space_id == space_id)
        )

        # Add time-based filtering if provided
        if start_date is not None:
            query = query.where(Document.updated_at >= start_date)
        if end_date is not None:
            query = query.where(Document.updated_at <= end_date)

        # Execute the query to get all chunks (will sort in Python)
        result = await self.db_session.execute(query)
        chunks = result.scalars().all()

        # Calculate similarity scores in Python and sort
        chunk_scores = []
        for chunk in chunks:
            if chunk.embedding:
                similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                chunk_scores.append((chunk, similarity))

        # Sort by similarity (descending) and take top_k
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        top_chunks = [chunk for chunk, _score in chunk_scores[:top_k]]

        return top_chunks

    async def full_text_search(
        self,
        query_text: str,
        top_k: int,
        space_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list:
        """Perform full-text keyword search on chunks.

        Args:
            query_text: The search query text
            top_k: Number of results to return
            space_id: The space ID to search within
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of chunks sorted by text relevance
        """
        from langflow.services.database.models import Chunk, Document
        from sqlalchemy import func, select
        from sqlalchemy.orm import joinedload

        # Create tsvector and tsquery for PostgreSQL full-text search
        tsvector = func.to_tsvector("english", Chunk.content)
        tsquery = func.plainto_tsquery("english", query_text)

        # Build the query filtered by space
        query = (
            select(Chunk)
            .options(joinedload(Chunk.document).joinedload(Document.space))
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.space_id == space_id)
            .where(tsvector.op("@@")(tsquery))  # Only include results that match
        )

        # Add time-based filtering if provided
        if start_date is not None:
            query = query.where(Document.updated_at >= start_date)
        if end_date is not None:
            query = query.where(Document.updated_at <= end_date)

        # Add text search ranking
        query = query.order_by(func.ts_rank_cd(tsvector, tsquery).desc()).limit(top_k)

        # Execute the query
        result = await self.db_session.execute(query)
        chunks = result.scalars().all()

        return chunks

    async def hybrid_search(
        self,
        query_text: str,
        top_k: int,
        space_id: int,
        document_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search that returns documents grouped by chunks.

        Each returned item is a document-grouped dict that preserves real DB chunk IDs
        for downstream citation with [citation:<chunk_id>].

        Uses Reciprocal Rank Fusion (RRF) to combine vector and full-text search results.

        Args:
            query_text: The search query text
            top_k: Number of documents to return
            space_id: The space ID to search within
            document_type: Optional document type to filter results
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of dictionaries containing document data with chunks and scores
        """
        from langflow.services.database.models import Chunk, Document, DocumentType
        from langflow.services.deps import get_settings
        from sqlalchemy import func, select
        from sqlalchemy.orm import joinedload

        # Get embedding for the query
        settings = get_settings()
        embedding_model = settings.embedding_model_instance
        query_embedding = embedding_model.embed(query_text)

        # RRF constants
        k = 60
        n_results = top_k * 5  # Fetch extra chunks for better document-level fusion

        # Base conditions for chunk filtering
        base_conditions = [Document.space_id == space_id]

        # Add document type filter if provided
        if document_type is not None:
            if isinstance(document_type, str):
                try:
                    doc_type_enum = DocumentType[document_type]
                    base_conditions.append(Document.doc_type == doc_type_enum)
                except KeyError:
                    return []
            else:
                base_conditions.append(Document.doc_type == document_type)

        # Add time-based filtering
        if start_date is not None:
            base_conditions.append(Document.updated_at >= start_date)
        if end_date is not None:
            base_conditions.append(Document.updated_at <= end_date)

        # Get chunks for semantic search
        semantic_query = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(*base_conditions)
        )
        semantic_result = await self.db_session.execute(semantic_query)
        semantic_chunks = semantic_result.scalars().all()

        # Calculate similarity scores for semantic search
        semantic_scores = []
        for rank, chunk in enumerate(semantic_chunks, start=1):
            if chunk.embedding:
                similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                semantic_scores.append((chunk.id, rank, similarity))

        # Sort by similarity and take top n_results
        semantic_scores.sort(key=lambda x: x[2], reverse=True)
        semantic_results = {
            chunk_id: rank for chunk_id, rank, _sim in semantic_scores[:n_results]
        }

        # Get chunks for keyword search (using PostgreSQL full-text search)
        tsvector = func.to_tsvector("english", Chunk.content)
        tsquery = func.plainto_tsquery("english", query_text)

        keyword_query = (
            select(
                Chunk.id,
                func.rank().over(order_by=func.ts_rank_cd(tsvector, tsquery).desc()).label("rank"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(*base_conditions)
            .where(tsvector.op("@@")(tsquery))
            .order_by(func.ts_rank_cd(tsvector, tsquery).desc())
            .limit(n_results)
        )

        keyword_result = await self.db_session.execute(keyword_query)
        keyword_results = {chunk_id: rank for chunk_id, rank in keyword_result.all()}

        # Combine results using Reciprocal Rank Fusion
        rrf_scores: dict[int, float] = {}
        all_chunk_ids = set(semantic_results.keys()) | set(keyword_results.keys())

        for chunk_id in all_chunk_ids:
            semantic_rank = semantic_results.get(chunk_id, 0)
            keyword_rank = keyword_results.get(chunk_id, 0)

            rrf_score = (1.0 / (k + semantic_rank) if semantic_rank > 0 else 0.0) + (
                1.0 / (k + keyword_rank) if keyword_rank > 0 else 0.0
            )
            rrf_scores[chunk_id] = rrf_score

        # Get top chunks by RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[
            :n_results
        ]

        if not sorted_chunk_ids:
            return []

        # Fetch chunks with documents
        chunks_query = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .where(Chunk.id.in_(sorted_chunk_ids))
        )
        chunks_result = await self.db_session.execute(chunks_query)
        chunks_with_docs = chunks_result.scalars().all()

        # Convert to serializable dictionaries
        serialized_chunk_results: list[dict[str, Any]] = []
        for chunk in chunks_with_docs:
            serialized_chunk_results.append(
                {
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "score": float(rrf_scores.get(chunk.id, 0.0)),
                    "document": {
                        "id": chunk.document.id,
                        "title": chunk.document.title,
                        "document_type": chunk.document.doc_type.value
                        if hasattr(chunk.document, "doc_type")
                        else None,
                        "metadata": {},  # TODO: Add metadata if needed
                    },
                }
            )

        # Group by document, preserving ranking order by best chunk rank
        doc_scores: dict[int, float] = {}
        doc_order: list[int] = []
        for item in serialized_chunk_results:
            doc_id = item.get("document", {}).get("id")
            if doc_id is None:
                continue
            if doc_id not in doc_scores:
                doc_scores[doc_id] = item.get("score", 0.0)
                doc_order.append(doc_id)
            else:
                # Use the best score as doc score
                doc_scores[doc_id] = max(doc_scores[doc_id], item.get("score", 0.0))

        # Keep only top_k documents by initial rank order
        doc_ids = doc_order[:top_k]
        if not doc_ids:
            return []

        # Fetch ALL chunks for selected documents in a single query
        all_chunks_query = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.id.in_(doc_ids))
            .where(*base_conditions)
            .order_by(Chunk.document_id, Chunk.id)
        )
        all_chunks_result = await self.db_session.execute(all_chunks_query)
        all_chunks = all_chunks_result.scalars().all()

        # Assemble final doc-grouped results
        doc_map: dict[int, dict[str, Any]] = {
            doc_id: {
                "document_id": doc_id,
                "content": "",
                "score": float(doc_scores.get(doc_id, 0.0)),
                "chunks": [],
                "document": {},
                "source": None,
            }
            for doc_id in doc_ids
        }

        for chunk in all_chunks:
            doc = chunk.document
            doc_id = doc.id
            if doc_id in doc_map:
                doc_entry = doc_map[doc_id]
                doc_entry["document"] = {
                    "id": doc.id,
                    "title": doc.title,
                    "document_type": doc.doc_type.value
                    if hasattr(doc, "doc_type")
                    else None,
                    "metadata": {},  # TODO: Add metadata
                }
                doc_entry["source"] = (
                    doc.doc_type.value if hasattr(doc, "doc_type") else None
                )
                doc_entry["chunks"].append({"chunk_id": chunk.id, "content": chunk.content})

        # Fill concatenated content (useful for reranking)
        final_docs: list[dict[str, Any]] = []
        for doc_id in doc_ids:
            if doc_id in doc_map:
                entry = doc_map[doc_id]
                entry["content"] = "\n\n".join(
                    c["content"] for c in entry.get("chunks", []) if c.get("content")
                )
                final_docs.append(entry)

        return final_docs
