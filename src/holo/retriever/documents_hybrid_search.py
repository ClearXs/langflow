"""Document-level hybrid search retriever for Holo knowledge system.

This module provides hybrid search combining vector similarity and full-text search
for documents. Adapted from SurfSense for Langflow integration.

CRITICAL NOTE: Since we removed pgvector dependency, this implementation uses:
- JSON-based embeddings (stored as list[float])
- Cosine similarity calculated in Python instead of PostgreSQL <=> operator
- Full-text search still uses PostgreSQL's to_tsvector/plainto_tsquery
"""

from datetime import datetime
from typing import Any


class DocumentHybridSearchRetriever:
    """Retriever for hybrid search on documents using vector + full-text search."""

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
        """Perform vector similarity search on documents.

        Args:
            query_text: The search query text
            top_k: Number of results to return
            space_id: The space ID to search within
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of documents sorted by vector similarity
        """
        from langflow.services.database.models import Document

        # Get embedding for the query
        # TODO: Get embedding model from Langflow config
        from langflow.services.deps import get_settings
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        settings = get_settings()
        embedding_model = settings.embedding_model_instance
        query_embedding = embedding_model.embed(query_text)

        # Build the query filtered by space
        query = (
            select(Document)
            .options(joinedload(Document.space))
            .where(Document.space_id == space_id)
        )

        # Add time-based filtering if provided
        if start_date is not None:
            query = query.where(Document.updated_at >= start_date)
        if end_date is not None:
            query = query.where(Document.updated_at <= end_date)

        # Execute the query to get all documents (will sort in Python)
        result = await self.db_session.execute(query)
        documents = result.scalars().all()

        # Calculate similarity scores in Python and sort
        doc_scores = []
        for doc in documents:
            if doc.embedding:
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                doc_scores.append((doc, similarity))

        # Sort by similarity (descending) and take top_k
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        top_documents = [doc for doc, _score in doc_scores[:top_k]]

        return top_documents

    async def full_text_search(
        self,
        query_text: str,
        top_k: int,
        space_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list:
        """Perform full-text keyword search on documents.

        Args:
            query_text: The search query text
            top_k: Number of results to return
            space_id: The space ID to search within
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of documents sorted by text relevance
        """
        from langflow.services.database.models import Document
        from sqlalchemy import func, select
        from sqlalchemy.orm import joinedload

        # Create tsvector and tsquery for PostgreSQL full-text search
        tsvector = func.to_tsvector("english", Document.content)
        tsquery = func.plainto_tsquery("english", query_text)

        # Build the query filtered by space
        query = (
            select(Document)
            .options(joinedload(Document.space))
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
        documents = result.scalars().all()

        return documents

    async def hybrid_search(
        self,
        query_text: str,
        top_k: int,
        space_id: int,
        document_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search that returns documents with their chunks.

        Uses Reciprocal Rank Fusion (RRF) to combine vector and full-text search results.

        Args:
            query_text: The search query text
            top_k: Number of documents to return
            space_id: The space ID to search within
            document_type: Optional document type to filter results
            start_date: Optional start date for filtering documents by updated_at
            end_date: Optional end date for filtering documents by updated_at

        Returns:
            List of document dictionaries with chunks and metadata
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
        n_results = top_k * 2  # Fetch extra documents for better fusion

        # Base conditions for document filtering
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

        # Get documents for semantic search
        semantic_query = select(Document).where(*base_conditions)
        semantic_result = await self.db_session.execute(semantic_query)
        semantic_docs = semantic_result.scalars().all()

        # Calculate similarity scores for semantic search
        semantic_scores = []
        for rank, doc in enumerate(semantic_docs, start=1):
            if doc.embedding:
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                semantic_scores.append((doc.id, rank, similarity))

        # Sort by similarity and take top n_results
        semantic_scores.sort(key=lambda x: x[2], reverse=True)
        semantic_results = {
            doc_id: rank for doc_id, rank, _sim in semantic_scores[:n_results]
        }

        # Get documents for keyword search (using PostgreSQL full-text search)
        tsvector = func.to_tsvector("english", Document.content)
        tsquery = func.plainto_tsquery("english", query_text)

        keyword_query = (
            select(
                Document.id,
                func.rank().over(order_by=func.ts_rank_cd(tsvector, tsquery).desc()).label("rank"),
            )
            .where(*base_conditions)
            .where(tsvector.op("@@")(tsquery))
            .order_by(func.ts_rank_cd(tsvector, tsquery).desc())
            .limit(n_results)
        )

        keyword_result = await self.db_session.execute(keyword_query)
        keyword_results = {doc_id: rank for doc_id, rank in keyword_result.all()}

        # Combine results using Reciprocal Rank Fusion
        rrf_scores: dict[int, float] = {}
        all_doc_ids = set(semantic_results.keys()) | set(keyword_results.keys())

        for doc_id in all_doc_ids:
            semantic_rank = semantic_results.get(doc_id, 0)
            keyword_rank = keyword_results.get(doc_id, 0)

            rrf_score = (1.0 / (k + semantic_rank) if semantic_rank > 0 else 0.0) + (
                1.0 / (k + keyword_rank) if keyword_rank > 0 else 0.0
            )
            rrf_scores[doc_id] = rrf_score

        # Get top_k document IDs by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[
            :top_k
        ]

        if not sorted_doc_ids:
            return []

        # Fetch documents and chunks
        docs_query = (
            select(Document).options(joinedload(Document.space)).where(Document.id.in_(sorted_doc_ids))
        )
        docs_result = await self.db_session.execute(docs_query)
        documents_dict = {doc.id: doc for doc in docs_result.scalars().all()}

        # Fetch ALL chunks for these documents
        chunks_query = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .where(Chunk.document_id.in_(sorted_doc_ids))
            .order_by(Chunk.document_id, Chunk.id)
        )
        chunks_result = await self.db_session.execute(chunks_query)
        chunks = chunks_result.scalars().all()

        # Assemble doc-grouped results
        doc_map: dict[int, dict[str, Any]] = {
            doc_id: {
                "document_id": doc_id,
                "content": "",
                "score": float(rrf_scores[doc_id]),
                "chunks": [],
                "document": {
                    "id": documents_dict[doc_id].id,
                    "title": documents_dict[doc_id].title,
                    "document_type": documents_dict[doc_id].doc_type.value
                    if hasattr(documents_dict[doc_id], "doc_type")
                    else None,
                    "metadata": {},  # TODO: Add metadata field if needed
                },
                "source": documents_dict[doc_id].doc_type.value
                if hasattr(documents_dict[doc_id], "doc_type")
                else None,
            }
            for doc_id in sorted_doc_ids
            if doc_id in documents_dict
        }

        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id in doc_map:
                doc_map[doc_id]["chunks"].append({"chunk_id": chunk.id, "content": chunk.content})

        # Fill concatenated content
        final_docs: list[dict[str, Any]] = []
        for doc_id in sorted_doc_ids:
            if doc_id in doc_map:
                entry = doc_map[doc_id]
                entry["content"] = "\n\n".join(
                    c["content"] for c in entry.get("chunks", []) if c.get("content")
                )
                final_docs.append(entry)

        return final_docs
