"""Hybrid Retrieval Service.

Combines multiple retrieval strategies:
1. Vector similarity search (PGVector + HNSW)
2. Full-text search (TSVECTOR + GIN)
3. Graph traversal (Neo4j via LightRAG)
4. RRF (Reciprocal Rank Fusion) for result merging
"""

import logging
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    """Service for hybrid document and chunk retrieval."""

    def __init__(self):
        """Initialize hybrid retrieval service."""
        self.rrf_constant = 60  # RRF k parameter (常数)
        self.graph_weight = 1.0
        self.graph_recall_limit = None
        self.graph_relation_types: list[str] | None = None

        try:
            from langflow.services.graph.config import kg_config

            weight = float(kg_config.graph_rrf_weight)
            self.graph_weight = max(0.0, min(5.0, weight))

            if kg_config.graph_recall_limit and kg_config.graph_recall_limit > 0:
                self.graph_recall_limit = kg_config.graph_recall_limit

            if kg_config.graph_relation_types:
                raw_types = [t.strip().upper() for t in kg_config.graph_relation_types.split(",")]
                self.graph_relation_types = [t for t in raw_types if t]
        except Exception as e:
            logger.warning(f"Failed to load graph retrieval config: {e}")

    async def search(
        self,
        query: str,
        space_id: int,
        session: AsyncSession,
        top_k: int = 10,
        enable_vector: bool = True,
        enable_fts: bool = True,
        enable_graph: bool = False,
        mentioned_document_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """Hybrid search combining vector, full-text, and graph retrieval.

        Args:
            query: Search query text
            space_id: Space ID to search within
            session: Database session
            top_k: Number of results to return
            enable_vector: Enable vector similarity search
            enable_fts: Enable full-text search
            enable_graph: Enable knowledge graph search
            mentioned_document_ids: Optional document IDs to limit search scope

        Returns:
            Dictionary with:
                - chunks: List of retrieved chunks with scores
                - graph_answer: Graph query answer (if enabled)
                - sources: Deduplicated source documents
        """
        logger.info(
            f"Hybrid search: query='{query[:50]}...', space_id={space_id}, "
            f"vector={enable_vector}, fts={enable_fts}, graph={enable_graph}"
        )

        # Step 1: Generate query embedding (if vector search enabled)
        query_embedding = None
        if enable_vector:
            try:
                from langflow.services.etl.embeddings import get_embedding_service

                embedding_service = get_embedding_service()
                query_embedding = await embedding_service.embed_text(query)
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                enable_vector = False

        # Step 2: Vector similarity search
        vector_results = []
        if enable_vector and query_embedding:
            try:
                vector_results = await self._vector_search(
                    session=session,
                    space_id=space_id,
                    query_embedding=query_embedding,
                    top_k=top_k * 2,  # Get more candidates for RRF
                    mentioned_document_ids=mentioned_document_ids
                )
                logger.info(f"Vector search returned {len(vector_results)} results")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")

        # Step 3: Full-text search
        fts_results = []
        if enable_fts:
            try:
                fts_results = await self._fulltext_search(
                    session=session,
                    space_id=space_id,
                    query=query,
                    top_k=top_k * 2,  # Get more candidates for RRF
                    mentioned_document_ids=mentioned_document_ids
                )
                logger.info(f"Full-text search returned {len(fts_results)} results")
            except Exception as e:
                logger.error(f"Full-text search failed: {e}")

        # Step 4: Graph search (if enabled)
        graph_answer = None
        graph_results = []
        graph_doc_ids = []
        graph_entity_ids = []
        graph_chunk_ids = []
        if enable_graph:
            try:
                from langflow.services.graph import get_graph_service

                graph_service = get_graph_service()
                graph_answer = await graph_service.query_graph(
                    query=query,
                    space_id=space_id,
                    mode="hybrid",
                    top_k=top_k
                )
                graph_top_k = top_k * 2
                if self.graph_recall_limit:
                    graph_top_k = min(graph_top_k, self.graph_recall_limit)
                graph_results, graph_doc_ids, graph_entity_ids, graph_chunk_ids = await self._graph_search(
                    session=session,
                    query=query,
                    space_id=space_id,
                    top_k=graph_top_k,
                    mentioned_document_ids=mentioned_document_ids,
                    relation_types=self.graph_relation_types,
                    recall_limit=self.graph_recall_limit,
                )
                logger.info("Graph search completed")
            except Exception as e:
                logger.error(f"Graph search failed: {e}")

        # Step 5: RRF fusion
        chunks = await self._rrf_fusion(
            session=session,
            vector_results=vector_results,
            fts_results=fts_results,
            graph_results=graph_results,
            top_k=top_k
        )

        logger.info(f"RRF fusion returned {len(chunks)} final results")

        # Step 6: Extract source documents
        sources = await self._extract_sources(chunks)

        # Step 7: Validate graph answer consistency
        graph_validation = self._validate_graph_answer(graph_answer, graph_doc_ids, chunks)
        graph_sources = self._build_graph_sources(
            graph_answer=graph_answer,
            entity_ids=graph_entity_ids,
            document_ids=graph_doc_ids,
            chunk_ids=graph_chunk_ids,
        )
        if graph_sources:
            graph_paths = await self._build_graph_paths(
                session=session,
                space_id=space_id,
                entity_ids=graph_entity_ids,
                relation_types=self.graph_relation_types,
                limit=self.graph_recall_limit,
            )
            graph_sources["paths"] = graph_paths

        return {
            "chunks": chunks,
            "graph_answer": graph_answer,
            "graph_sources": graph_sources,
            "graph_validation": graph_validation,
            "sources": sources
        }

    async def _vector_search(
        self,
        session: AsyncSession,
        space_id: int,
        query_embedding: list[float],
        top_k: int,
        mentioned_document_ids: list[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Vector similarity search using external vector store (Chroma/Milvus/etc).

        Returns:
            List of (chunk_id, score) tuples
        """
        try:
            from langflow.services.vector import get_vector_store

            vector_store = get_vector_store()
            await vector_store.initialize()

            collection_name = f"space_{space_id}_chunks"

            # Check if collection exists
            if not await vector_store.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} does not exist, returning empty results")
                return []

            # Build filter for mentioned documents
            filter_dict = {}
            if mentioned_document_ids:
                # Chroma doesn't support $in operator, we'll filter in Python
                # For now, search without filter and filter results afterward
                pass

            # Perform vector search
            results = await vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                top_k=top_k * 2 if mentioned_document_ids else top_k,  # Get more if we need to filter
                filter_dict=filter_dict,
            )

            # Filter by mentioned documents if needed
            if mentioned_document_ids:
                results = [r for r in results if r.metadata.get("document_id") in mentioned_document_ids]
                results = results[:top_k]  # Limit to top_k after filtering

            # Convert to (chunk_id, score) tuples
            return [(result.chunk_id, result.score) for result in results]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Fallback to empty results instead of crashing
            return []

    async def _fulltext_search(
        self,
        session: AsyncSession,
        space_id: int,
        query: str,
        top_k: int,
        mentioned_document_ids: list[int] | None = None
    ) -> list[tuple[int, float]]:
        """Full-text search using PostgreSQL tsvector.

        Returns:
            List of (chunk_id, rank) tuples
        """
        from langflow.services.database.models.chunk import Chunk

        # Create tsquery
        tsquery = func.to_tsquery("english", query)

        # Build query
        query_stmt = select(
            Chunk.id,
            func.ts_rank_cd(Chunk.tsvector, tsquery).label("rank")
        ).where(
            Chunk.space_id == space_id,
            Chunk.tsvector.op("@@")(tsquery)
        )

        # Filter by mentioned documents if provided
        if mentioned_document_ids:
            query_stmt = query_stmt.where(Chunk.document_id.in_(mentioned_document_ids))

        # Order by rank and limit
        query_stmt = query_stmt.order_by(text("rank DESC")).limit(top_k)

        # Execute
        result = await session.execute(query_stmt)
        rows = result.all()

        return [(row.id, row.rank) for row in rows]

    async def _rrf_fusion(
        self,
        session: AsyncSession,
        vector_results: list[tuple[int, float]],
        fts_results: list[tuple[int, float]],
        graph_results: list[tuple[int, float]],
        top_k: int
    ) -> list[dict]:
        """Reciprocal Rank Fusion to combine vector, FTS, and graph results.

        RRF formula: score(chunk) = sum(1 / (k + rank_i))
        where k is a constant (default 60) and rank_i is the rank in each retrieval method.

        Returns:
            List of chunk dictionaries with combined scores
        """
        from langflow.services.database.models.chunk import Chunk

        # Create rank maps
        vector_ranks = {chunk_id: idx + 1 for idx, (chunk_id, _) in enumerate(vector_results)}
        fts_ranks = {chunk_id: idx + 1 for idx, (chunk_id, _) in enumerate(fts_results)}
        graph_ranks = {chunk_id: idx + 1 for idx, (chunk_id, _) in enumerate(graph_results)}

        # Get all unique chunk IDs
        all_chunk_ids = set(vector_ranks.keys()) | set(fts_ranks.keys()) | set(graph_ranks.keys())

        # Calculate RRF scores
        rrf_scores = {}
        for chunk_id in all_chunk_ids:
            vector_score = 1.0 / (self.rrf_constant + vector_ranks.get(chunk_id, 999)) if chunk_id in vector_ranks else 0
            fts_score = 1.0 / (self.rrf_constant + fts_ranks.get(chunk_id, 999)) if chunk_id in fts_ranks else 0
            graph_score = 1.0 / (self.rrf_constant + graph_ranks.get(chunk_id, 999)) if chunk_id in graph_ranks else 0

            rrf_scores[chunk_id] = vector_score + fts_score + (graph_score * self.graph_weight)

        # Sort by RRF score
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch chunk details
        chunk_ids = [chunk_id for chunk_id, _ in sorted_chunks]
        if not chunk_ids:
            return []

        result = await session.execute(
            select(Chunk).where(Chunk.id.in_(chunk_ids))
        )
        chunks_map = {chunk.id: chunk for chunk in result.scalars().all()}

        # Build result with scores
        results = []
        for chunk_id, score in sorted_chunks:
            if chunk_id in chunks_map:
                chunk = chunks_map[chunk_id]
                results.append({
                    "id": chunk.id,
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                    "score": score,
                    "vector_rank": vector_ranks.get(chunk_id),
                    "fts_rank": fts_ranks.get(chunk_id),
                    "graph_rank": graph_ranks.get(chunk_id),
                })

        return results

    async def _graph_search(
        self,
        session: AsyncSession,
        query: str,
        space_id: int,
        top_k: int,
        mentioned_document_ids: list[int] | None = None,
        relation_types: list[str] | None = None,
        recall_limit: int | None = None,
    ) -> tuple[list[tuple[int, float]], list[int], list[int], list[int]]:
        """Graph-informed search using entity vectors and graph bindings.

        Returns:
            Tuple of:
                - List of (chunk_id, score) tuples
                - List of related document IDs
        """
        try:
            from sqlalchemy import case

            from langflow.services.database.models.chunk import Chunk
            from langflow.services.database.models.entity import Entity
            from langflow.services.database.models.relation import Relation
            from langflow.services.etl.embeddings import get_embedding_service
            from langflow.services.vector.entity_vector_store import EntityVectorStore

            embedding_service = get_embedding_service()
            query_vector = await embedding_service.embed_text(query)

            vector_store = EntityVectorStore()
            entity_results = await vector_store.search_entity_vectors(
                space_id=space_id,
                query_vector=query_vector,
                top_k=top_k,
            )

            if not entity_results:
                return [], [], [], []

            entity_ids = [
                int(result.metadata.get("entity_id") if result.metadata else result.chunk_id)
                for result in entity_results
            ]

            related_entity_ids: set[int] = set()
            if relation_types:
                normalized_types = [t.strip().upper() for t in relation_types if t and t.strip()]
                if normalized_types:
                    stmt_rel = (
                        select(Relation.source_entity_id, Relation.target_entity_id)
                        .where(Relation.space_id == space_id)
                        .where(Relation.relation_type.in_(normalized_types))
                        .where(
                            (Relation.source_entity_id.in_(entity_ids))
                            | (Relation.target_entity_id.in_(entity_ids))
                        )
                    )
                    result_rel = await session.execute(stmt_rel)
                    for source_id, target_id in result_rel.all():
                        if source_id:
                            related_entity_ids.add(int(source_id))
                        if target_id:
                            related_entity_ids.add(int(target_id))

            all_entity_ids = list(set(entity_ids) | related_entity_ids)

            stmt = select(Entity).where(Entity.id.in_(all_entity_ids))
            result = await session.execute(stmt)
            entities = result.scalars().all()

            entity_rank = {entity_id: idx + 1 for idx, entity_id in enumerate(entity_ids)}
            related_rank_base = max(entity_rank.values(), default=0) + 1
            doc_rank: dict[int, int] = {}
            for entity in entities:
                if entity.document_id is None:
                    continue
                rank = entity_rank.get(entity.id, related_rank_base)
                if entity.document_id not in doc_rank or rank < doc_rank[entity.document_id]:
                    doc_rank[entity.document_id] = rank

            document_ids = [doc_id for doc_id, _ in sorted(doc_rank.items(), key=lambda item: item[1])]
            if mentioned_document_ids:
                document_ids = [doc_id for doc_id in document_ids if doc_id in mentioned_document_ids]

            if not document_ids:
                return [], [], entity_ids, []

            if recall_limit and len(document_ids) > recall_limit:
                document_ids = document_ids[:recall_limit]

            ordering = case({doc_id: rank for doc_id, rank in doc_rank.items()}, value=Chunk.document_id)

            stmt_chunks = (
                select(Chunk.id)
                .where(Chunk.space_id == space_id, Chunk.document_id.in_(document_ids))
                .order_by(ordering, Chunk.chunk_index.asc())
                .limit(top_k)
            )
            result_chunks = await session.execute(stmt_chunks)
            chunk_ids = [row.id for row in result_chunks.all()]

            return ([(chunk_id, float(idx + 1)) for idx, chunk_id in enumerate(chunk_ids)], document_ids, entity_ids, chunk_ids)

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return [], [], [], []

    @staticmethod
    def _validate_graph_answer(
        graph_answer: str | None,
        graph_doc_ids: list[int],
        chunks: list[dict],
    ) -> dict[str, Any] | None:
        """Validate graph_answer consistency with graph/doc evidence.

        Returns:
            Validation dict or None if no graph_answer.
        """
        if graph_answer is None:
            return None

        if not graph_doc_ids:
            return {"status": "no_graph_hits", "matched_doc_ids": [], "chunk_doc_ids": []}

        chunk_doc_ids = sorted({chunk["document_id"] for chunk in chunks})
        matched_doc_ids = sorted(set(graph_doc_ids) & set(chunk_doc_ids))

        status = "ok" if matched_doc_ids else "graph_unlinked"

        return {
            "status": status,
            "matched_doc_ids": matched_doc_ids,
            "chunk_doc_ids": chunk_doc_ids,
        }

    @staticmethod
    def _build_graph_sources(
        graph_answer: str | None,
        entity_ids: list[int],
        document_ids: list[int],
        chunk_ids: list[int],
    ) -> dict[str, Any] | None:
        """Build graph answer sources for tracing."""
        if graph_answer is None:
            return None

        return {
            "entity_ids": sorted(set(entity_ids)),
            "document_ids": sorted(set(document_ids)),
            "chunk_ids": sorted(set(chunk_ids)),
        }

    @staticmethod
    async def _build_graph_paths(
        session: AsyncSession,
        space_id: int,
        entity_ids: list[int],
        relation_types: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not entity_ids:
            return []

        from langflow.services.database.models.relation import Relation

        stmt = (
            select(Relation)
            .where(Relation.space_id == space_id)
            .where(Relation.source_entity_id.in_(entity_ids))
            .where(Relation.target_entity_id.in_(entity_ids))
        )
        if relation_types:
            stmt = stmt.where(Relation.relation_type.in_(relation_types))
        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        relations = result.scalars().all()

        return [
            {
                "source_entity_id": rel.source_entity_id,
                "target_entity_id": rel.target_entity_id,
                "relation_type": rel.relation_type,
                "document_id": rel.document_id,
                "chunk_id": rel.chunk_id,
                "weight": rel.weight,
            }
            for rel in relations
        ]

    async def _extract_sources(self, chunks: list[dict]) -> list[dict]:
        """Extract unique source documents from chunks.

        Returns:
            List of source document info
        """
        seen_docs = set()
        sources = []

        for chunk in chunks:
            doc_id = chunk["document_id"]
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                sources.append({
                    "document_id": doc_id,
                    "chunk_preview": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                })

        return sources


# Global instance
_retrieval_service = None


def get_retrieval_service() -> HybridRetrievalService:
    """Get or create global retrieval service instance."""
    global _retrieval_service

    if _retrieval_service is None:
        _retrieval_service = HybridRetrievalService()

    return _retrieval_service
