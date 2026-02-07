"""Knowledge Graph Service using LightRAG.

This service provides:
- Automatic entity extraction from documents
- Automatic relation extraction
- Graph storage in Neo4j
- Vector storage in Milvus
- Hybrid graph + vector querying
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Service for knowledge graph extraction and querying using LightRAG."""

    def __init__(self):
        """Initialize knowledge graph service."""
        self._rag_instances = {}  # Cache: space_id → LightRAG instance
        self._initialized = False

    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            import lightrag  # noqa: F401
            return True
        except ImportError:
            logger.warning("LightRAG not installed. Knowledge graph features disabled.")
            return False

    def _get_rag_instance(self, space_id: int):
        """Get or create LightRAG instance for a space.

        Args:
            space_id: Space ID

        Returns:
            LightRAG instance or None if dependencies not available
        """
        from langflow.services.graph.config import kg_config

        # Check if enabled and configured
        if not kg_config.is_available():
            logger.info("Knowledge graph not available (disabled or not configured)")
            return None

        # Check dependencies
        if not self._check_dependencies():
            return None

        # Return cached instance
        if space_id in self._rag_instances:
            return self._rag_instances[space_id]

        try:
            from lightrag import LightRAG
            try:
                from lightrag.llm import openai_complete_if_cache, openai_embedding
                embedding_func = openai_embedding
            except ImportError:
                from lightrag.llm.openai import (  # type: ignore[assignment]
                    openai_complete_if_cache,
                    openai_embed,
                )
                from lightrag.utils import wrap_embedding_func_with_attrs

                embedding_model = kg_config.get_embedding_model()
                if embedding_model != "openai":
                    raise RuntimeError(
                        f"LightRAG embedding model '{embedding_model}' is not supported with current bindings."
                    )

                from langflow.services.llm.config import llm_config

                embedding_dim = kg_config.get_embedding_dimension()
                embedding_model_name = llm_config.openai_embedding_model
                embedding_base_url = kg_config.get_llm_base_url()
                embedding_api_key = kg_config.get_embedding_api_key()
                max_token_size = getattr(openai_embed, "max_token_size", None)

                base_embed = openai_embed.func if hasattr(openai_embed, "func") else openai_embed

                @wrap_embedding_func_with_attrs(
                    embedding_dim=embedding_dim,
                    max_token_size=max_token_size,
                    model_name=embedding_model_name,
                )
                async def _openai_embedding(texts, **kwargs):
                    return await base_embed(
                        texts,
                        model=embedding_model_name,
                        base_url=embedding_base_url,
                        api_key=embedding_api_key,
                        **kwargs,
                    )

                embedding_func = _openai_embedding

            # Configure LightRAG storage backends via environment variables
            workspace = f"space_{space_id}"
            os.environ.setdefault("WORKSPACE", workspace)
            if kg_config.neo4j_enabled:
                os.environ["NEO4J_URI"] = kg_config.neo4j_uri
                os.environ["NEO4J_USERNAME"] = kg_config.neo4j_username
                os.environ["NEO4J_PASSWORD"] = kg_config.neo4j_password or os.getenv("NEO4J_PASSWORD", "")
                os.environ.setdefault("NEO4J_DATABASE", kg_config.neo4j_database)
                os.environ.setdefault("NEO4J_WORKSPACE", workspace)

            use_milvus_storage = (
                os.getenv("LANGFLOW_KG_USE_MILVUS", "false").lower() == "true"
                and kg_config.milvus_enabled
            )
            if use_milvus_storage:
                from langflow.services.vector.config import vector_config

                milvus_uri = os.getenv("MILVUS_URI")
                if not milvus_uri:
                    if vector_config.engine_type.lower() == "milvus":
                        if vector_config.milvus_host and (
                            "/" in vector_config.milvus_host
                            or vector_config.milvus_host.endswith(".db")
                        ):
                            milvus_uri = vector_config.milvus_host
                        else:
                            milvus_uri = (
                                f"http://{vector_config.milvus_host}:{vector_config.milvus_port}"
                            )
                    else:
                        milvus_uri = f"http://{kg_config.milvus_host}:{kg_config.milvus_port}"

                if milvus_uri and ".db:" in milvus_uri and not milvus_uri.startswith(("http://", "https://", "file://")):
                    milvus_uri = milvus_uri.split(".db:")[0] + ".db"

                if milvus_uri and milvus_uri.endswith(".db") and not milvus_uri.startswith(("http://", "https://", "file://")):
                    milvus_uri = f"file://{os.path.abspath(milvus_uri)}"

                if milvus_uri and milvus_uri.startswith(("http://", "https://")):
                    os.environ["MILVUS_URI"] = milvus_uri
                else:
                    raise RuntimeError(
                        "LightRAG Milvus storage requires a server URI (http/https)."
                    )

                if kg_config.milvus_user:
                    os.environ["MILVUS_USER"] = kg_config.milvus_user
                if kg_config.milvus_password:
                    os.environ["MILVUS_PASSWORD"] = kg_config.milvus_password

                if os.getenv("MILVUS_DB_NAME"):
                    pass
                elif vector_config.engine_type.lower() == "milvus":
                    os.environ["MILVUS_DB_NAME"] = vector_config.milvus_db_name
                else:
                    os.environ["MILVUS_DB_NAME"] = "default"

                os.environ.setdefault("MILVUS_WORKSPACE", workspace)

            # Create working directory for this space
            working_dir = Path(kg_config.working_dir) / f"space_{space_id}"
            working_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Initializing LightRAG for space {space_id} at {working_dir}")

            async def _llm_model_func(
                prompt: str,
                system_prompt: str | None = None,
                history_messages: list[dict[str, str]] | None = None,
                **kwargs,
            ) -> str:
                kwargs.pop("hashing_kv", None)
                return await openai_complete_if_cache(
                    model=kg_config.get_llm_model(),
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs,
                )

            # Initialize LightRAG
            rag = LightRAG(
                working_dir=str(working_dir),

                # LLM configuration (for entity extraction)
                llm_model_func=_llm_model_func,
                llm_model_name=kg_config.get_llm_model(),
                llm_model_max_async=kg_config.get_llm_max_async(),
                llm_model_kwargs={
                    "api_key": kg_config.get_llm_api_key(),
                    "base_url": kg_config.get_llm_base_url(),
                } if kg_config.get_llm_base_url() else {
                    "api_key": kg_config.get_llm_api_key()
                },

                # Embedding configuration
                embedding_func=embedding_func,
                embedding_batch_num=kg_config.get_embedding_batch_num(),
                embedding_func_max_async=kg_config.get_llm_max_async(),

                # Storage configuration
                graph_storage="Neo4JStorage" if kg_config.neo4j_enabled else "NetworkXStorage",
                vector_storage="MilvusVectorDBStorage" if use_milvus_storage else "NanoVectorDBStorage",
                kv_storage="JsonKVStorage",
            )

            # Cache instance
            self._rag_instances[space_id] = rag
            self._initialized = True

            logger.info(f"LightRAG initialized for space {space_id}")
            return rag

        except Exception as e:
            logger.error(f"Failed to initialize LightRAG for space {space_id}: {e}")
            return None

    async def extract_graph_from_document(
        self,
        document_id: int,
        content: str,
        space_id: int,
        title: str | None = None
    ) -> dict:
        """Extract knowledge graph from document content.

        Args:
            document_id: Document ID
            content: Document content (markdown)
            space_id: Space ID
            title: Document title (optional)

        Returns:
            Dictionary with extraction statistics:
            {
                "entity_count": int,
                "relation_count": int,
                "success": bool,
                "error": str | None
            }
        """
        from langflow.services.graph.config import kg_config

        # Check if enabled
        if not kg_config.enabled:
            logger.info("Knowledge graph extraction disabled")
            return {
                "entity_count": 0,
                "relation_count": 0,
                "success": False,
                "error": "Knowledge graph disabled"
            }

        # Get RAG instance
        rag = self._get_rag_instance(space_id)
        if not rag:
            return {
                "entity_count": 0,
                "relation_count": 0,
                "success": False,
                "error": "LightRAG not available"
            }

        try:
            logger.info(f"Extracting knowledge graph from document {document_id}")

            if hasattr(rag, "initialize_storages"):
                await rag.initialize_storages()

            # Insert document into LightRAG
            # This automatically:
            # 1. Extracts entities using LLM
            # 2. Extracts relations using LLM
            # 3. Generates entity descriptions
            # 4. Stores entities in Milvus (vector)
            # 5. Stores graph in Neo4j
            await rag.ainsert(
                input=content,
                ids=str(document_id),
            )

            # Get statistics
            stats = await self._get_graph_stats(space_id, document_id)

            logger.info(
                f"Knowledge graph extracted from document {document_id}: "
                f"{stats['entity_count']} entities, {stats['relation_count']} relations"
            )

            return {
                **stats,
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.error(f"Knowledge graph extraction failed for document {document_id}: {e}")
            return {
                "entity_count": 0,
                "relation_count": 0,
                "success": False,
                "error": str(e)
            }

    async def _get_graph_stats(self, space_id: int, document_id: int) -> dict:
        """Get graph statistics for a document.

        NOTE: This method is called BEFORE enrichment, so document_id field doesn't exist yet in Neo4j.
        We count ALL nodes/edges in the space to get approximate statistics.

        Args:
            space_id: Space ID
            document_id: Document ID (not used in query, kept for API compatibility)

        Returns:
            Dictionary with entity_count and relation_count
        """
        from langflow.services.graph.config import kg_config

        if not kg_config.neo4j_enabled:
            # Cannot get stats without Neo4j
            return {"entity_count": 0, "relation_count": 0}

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                kg_config.neo4j_uri,
                auth=(kg_config.neo4j_username, kg_config.neo4j_password or "")
            )

            async with driver.session(database=kg_config.neo4j_database) as session:
                # Count ALL entities in this space
                # NOTE: Cannot filter by document_id because LightRAG hasn't written it yet
                # The enrichment step adds document_id AFTER this method runs
                entity_result = await session.run(
                    f"""
                    MATCH (n:`space_{space_id}`)
                    RETURN count(n) as count
                    """
                )
                entity_record = await entity_result.single()
                entity_count = entity_record["count"] if entity_record else 0

                # Count ALL relations in this space
                relation_result = await session.run(
                    f"""
                    MATCH (a:`space_{space_id}`)-[r]-(b:`space_{space_id}`)
                    RETURN count(DISTINCT r) as count
                    """
                )
                relation_record = await relation_result.single()
                relation_count = relation_record["count"] if relation_record else 0

            await driver.close()

            return {
                "entity_count": entity_count,
                "relation_count": relation_count
            }

        except Exception as e:
            logger.warning(f"Failed to get graph stats: {e}")
            return {"entity_count": 0, "relation_count": 0}

    async def query_graph(
        self,
        query: str,
        space_id: int,
        mode: str | None = None,
        top_k: int | None = None
    ) -> str | None:
        """Query knowledge graph.

        Args:
            query: Natural language query
            space_id: Space ID
            mode: Query mode (naive, local, global, hybrid)
            top_k: Number of results

        Returns:
            LLM-generated answer or None if failed
        """
        from langflow.services.graph.config import kg_config

        # Check if enabled
        if not kg_config.enabled:
            return None

        # Get RAG instance
        rag = self._get_rag_instance(space_id)
        if not rag:
            return None

        try:
            query_mode = mode or kg_config.default_query_mode
            k = top_k or kg_config.default_top_k

            logger.info(f"Querying knowledge graph: mode={query_mode}, top_k={k}")

            # Query LightRAG
            response = await rag.aquery(
                query=query,
                param={
                    "mode": query_mode,
                    "top_k": k
                }
            )

            return response

        except Exception as e:
            logger.error(f"Knowledge graph query failed: {e}")
            return None

    async def delete_document_graph(self, document_id: int, space_id: int):
        """Delete graph data for a document.

        Args:
            document_id: Document ID
            space_id: Space ID
        """
        from langflow.services.graph.config import kg_config

        if not kg_config.neo4j_enabled:
            logger.info("Neo4j not enabled, skipping graph deletion")
            return

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                kg_config.neo4j_uri,
                auth=(kg_config.neo4j_username, kg_config.neo4j_password or "")
            )

            async with driver.session(database=kg_config.neo4j_database) as session:
                # Delete all nodes and relationships for this document
                await session.run(
                    f"""
                    MATCH (n:`space_{space_id}`)
                    WHERE n.document_id = $doc_id
                    DETACH DELETE n
                    """,
                    doc_id=document_id
                )

            await driver.close()

            logger.info(f"Deleted graph data for document {document_id}")

            # TODO: Also delete from Milvus

        except Exception as e:
            logger.error(f"Failed to delete graph data for document {document_id}: {e}")


# Global instance
_graph_service = None


def get_graph_service() -> KnowledgeGraphService:
    """Get or create global knowledge graph service instance."""
    global _graph_service

    if _graph_service is None:
        _graph_service = KnowledgeGraphService()

    return _graph_service
