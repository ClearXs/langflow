"""Neo4j graph query service for knowledge graph API."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from langflow.services.graph.config import kg_config

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str
    name: str | None
    entity_type: str | None
    description: str | None
    aliases: list[str]
    properties: dict[str, Any]
    space_id: int | None
    document_id: int | None
    chunk_id: int | None
    document_title: str | None = None  # Title of the source document


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation_type: str
    description: str | None
    weight: float | None
    properties: dict[str, Any]


@dataclass
class GraphQueryResult:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    raw_paths: list[dict[str, Any]]


class Neo4jGraphService:
    """Neo4j graph query service."""

    async def _get_driver(self):
        if not kg_config.neo4j_enabled:
            raise RuntimeError("Neo4j is not enabled")
        try:
            from neo4j import AsyncGraphDatabase
        except ImportError as exc:
            raise RuntimeError("Neo4j driver not installed") from exc

        return AsyncGraphDatabase.driver(
            kg_config.neo4j_uri,
            auth=(kg_config.neo4j_username, kg_config.neo4j_password or ""),
        )

    @staticmethod
    def _space_label(space_id: int) -> str:
        return f"space_{space_id}"

    @staticmethod
    def _normalize_relation_type(relation_type: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_]", "_", relation_type.strip())
        return normalized or "RELATED_TO"

    async def upsert_entity(self, space_id: int, entity_data: dict[str, Any]) -> str | None:
        """Create or update a Neo4j node and return graph_node_id."""
        if not kg_config.neo4j_enabled:
            return None

        label = self._space_label(space_id)
        query = (
            f"MERGE (n:`{label}` {{name: $name, entity_type: $entity_type}}) "
            "SET n.graph_node_id = coalesce(n.graph_node_id, randomUUID()), "
            "n.description = $description, "
            "n.aliases = $aliases, "
            "n.properties = $properties, "
            "n.space_id = $space_id, "
            "n.document_id = $document_id, "
            "n.chunk_id = $chunk_id "
            "RETURN n.graph_node_id AS graph_node_id"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as session:
                result = await session.run(
                    query,
                    name=entity_data.get("name"),
                    entity_type=entity_data.get("entity_type"),
                    description=entity_data.get("description"),
                    aliases=entity_data.get("aliases") or [],
                    properties=entity_data.get("properties") or {},
                    space_id=space_id,
                    document_id=entity_data.get("document_id"),
                    chunk_id=entity_data.get("chunk_id"),
                )
                record = await result.single()
        finally:
            await driver.close()

        return record["graph_node_id"] if record else None

    async def create_relation(
        self,
        space_id: int,
        source_node_id: str,
        target_node_id: str,
        relation_type: str,
        description: str | None,
        weight: float | None,
        properties: dict[str, Any] | None,
    ) -> str | None:
        """Create a Neo4j relation and return graph_edge_id."""
        if not kg_config.neo4j_enabled:
            return None

        label = self._space_label(space_id)
        rel_type = self._normalize_relation_type(relation_type)
        query = (
            f"MATCH (a:`{label}` {{graph_node_id: $source}}) "
            f"MATCH (b:`{label}` {{graph_node_id: $target}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            "SET r.graph_edge_id = coalesce(r.graph_edge_id, randomUUID()), "
            "r.relation_type = $relation_type, "
            "r.description = $description, "
            "r.weight = $weight, "
            "r.properties = $properties, "
            "r.space_id = $space_id "
            "RETURN r.graph_edge_id AS graph_edge_id"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as session:
                result = await session.run(
                    query,
                    source=source_node_id,
                    target=target_node_id,
                    relation_type=relation_type,
                    description=description,
                    weight=weight,
                    properties=properties or {},
                    space_id=space_id,
                )
                record = await result.single()
        finally:
            await driver.close()

        return record["graph_edge_id"] if record else None

    async def fetch_subgraph(
        self,
        space_id: int,
        graph_node_ids: list[str],
        depth: int = 1,
        limit: int = 200,
        session=None,  # Optional DB session for document title lookup
    ) -> GraphQueryResult:
        """Fetch a subgraph by graph_node_id list.

        Args:
            space_id: Space ID
            graph_node_ids: List of graph_node_id to start from
            depth: Traversal depth (1-5)
            limit: Maximum number of paths to return
            session: Optional SQLAlchemy session for document title lookup

        Returns:
            GraphQueryResult with nodes, edges, and raw paths
        """
        if not graph_node_ids:
            return GraphQueryResult(nodes=[], edges=[], raw_paths=[])

        label = self._space_label(space_id)
        safe_depth = max(1, min(depth, 5))
        query = (
            "UNWIND $node_ids AS gid "
            f"MATCH (n:`{label}`) "
            "WHERE coalesce(n.graph_node_id, elementId(n)) = gid "
            f"OPTIONAL MATCH p=(n)-[r*1..{safe_depth}]-(m:`{label}`) "
            "WITH n, p "
            "RETURN coalesce(p, (n)) AS p LIMIT $limit"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as neo4j_session:
                result = await neo4j_session.run(
                    query,
                    node_ids=graph_node_ids,
                    limit=limit,
                )
                records = await result.values()
        finally:
            await driver.close()

        # Build document_id -> title mapping if session provided
        doc_titles = await self._fetch_document_titles(records, session) if session else {}

        return self._build_result_from_paths(records, doc_titles)

    async def fetch_entity_relations(
        self,
        space_id: int,
        graph_node_id: str,
        direction: str = "both",
        limit: int = 200,
        session=None,  # Optional DB session for document title lookup
    ) -> GraphQueryResult:
        """Fetch relations for a single entity node."""
        label = self._space_label(space_id)

        if direction == "outgoing":
            match = "(n)-[r]->(m)"
        elif direction == "incoming":
            match = "(n)<-[r]-(m)"
        else:
            match = "(n)-[r]-(m)"

        query = (
            f"MATCH p=(n:`{label}` {{graph_node_id: $node_id}}){match} "
            "RETURN p LIMIT $limit"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as neo4j_session:
                result = await neo4j_session.run(query, node_id=graph_node_id, limit=limit)
                records = await result.values()
        finally:
            await driver.close()

        doc_titles = await self._fetch_document_titles(records, session) if session else {}
        return self._build_result_from_paths(records, doc_titles)

    async def fetch_space_graph(
        self,
        space_id: int,
        limit: int = 200,
        session=None,  # Optional DB session for document title lookup
    ) -> GraphQueryResult:
        """Fetch graph nodes/edges for an entire space."""
        label = self._space_label(space_id)
        query = (
            f"MATCH (n:`{label}`) "
            f"OPTIONAL MATCH p=(n)-[r]-(m:`{label}`) "
            "WITH n, p "
            "RETURN coalesce(p, (n)) AS p LIMIT $limit"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as neo4j_session:
                result = await neo4j_session.run(query, limit=limit)
                records = await result.values()
        finally:
            await driver.close()

        doc_titles = await self._fetch_document_titles(records, session) if session else {}
        return self._build_result_from_paths(records, doc_titles)

    async def fetch_document_graph(
        self,
        space_id: int,
        document_id: int,
        limit: int = 200,
        session=None,  # Optional DB session for document title lookup
    ) -> GraphQueryResult:
        """Fetch graph nodes/edges associated with a document."""
        label = self._space_label(space_id)
        query = (
            f"MATCH (n:`{label}`) "
            "WHERE n.document_id = $document_id "
            f"OPTIONAL MATCH p=(n)-[r]-(m:`{label}`) "
            "WITH n, p "
            "RETURN coalesce(p, (n)) AS p LIMIT $limit"
        )

        driver = await self._get_driver()
        try:
            async with driver.session(database=kg_config.neo4j_database) as neo4j_session:
                result = await neo4j_session.run(query, document_id=document_id, limit=limit)
                records = await result.values()
        finally:
            await driver.close()

        doc_titles = await self._fetch_document_titles(records, session) if session else {}
        return self._build_result_from_paths(records, doc_titles)

    async def enrich_lightrag_nodes_and_edges(
        self,
        space_id: int,
        document_id: int,
    ) -> dict[str, int]:
        """Enrich LightRAG nodes/edges with Langflow-required fields.

        This method adds fields that Langflow expects but LightRAG doesn't write:
        - Nodes: graph_node_id, name, space_id, document_id
        - Edges: graph_edge_id, relation_type, space_id

        The operation is idempotent - running it multiple times won't overwrite existing values.

        Args:
            space_id: Space ID containing the graph
            document_id: Document ID that was just processed by LightRAG

        Returns:
            Dictionary with enrichment statistics:
            {
                "nodes_enriched": int,
                "edges_enriched": int,
            }
        """
        if not kg_config.neo4j_enabled:
            return {"nodes_enriched": 0, "edges_enriched": 0}

        label = self._space_label(space_id)
        driver = await self._get_driver()

        try:
            async with driver.session(database=kg_config.neo4j_database) as session:
                # Step 1: Enrich nodes with Langflow-required fields
                # - graph_node_id: Generate UUID if missing
                # - name: Copy from entity_id (LightRAG's primary key)
                # - space_id, document_id: Add for filtering
                node_query = f"""
                MATCH (n:`{label}`)
                WHERE n.document_id IS NULL OR n.graph_node_id IS NULL
                SET n.graph_node_id = coalesce(n.graph_node_id, randomUUID()),
                    n.name = coalesce(n.name, n.entity_id),
                    n.space_id = $space_id,
                    n.document_id = coalesce(n.document_id, $document_id)
                RETURN count(n) as enriched_count
                """

                node_result = await session.run(
                    node_query,
                    space_id=space_id,
                    document_id=document_id,
                )
                node_record = await node_result.single()
                nodes_enriched = node_record["enriched_count"] if node_record else 0

                # Step 2: Enrich relationships with Langflow-required fields
                # - graph_edge_id: Generate UUID if missing
                # - relation_type: Extract from keywords (LightRAG stores semantic info here)
                #   Priority: first keyword > truncated description > relationship type
                # - space_id: Add for filtering
                edge_query = f"""
                MATCH (a:`{label}`)-[r]-(b:`{label}`)
                WHERE r.graph_edge_id IS NULL OR r.relation_type IS NULL
                WITH r,
                     CASE
                       WHEN r.keywords IS NOT NULL AND r.keywords <> ''
                       THEN split(r.keywords, ',')[0]
                       WHEN r.description IS NOT NULL AND size(r.description) > 0
                       THEN substring(r.description, 0, 50)
                       ELSE type(r)
                     END as derived_relation_type
                SET r.graph_edge_id = coalesce(r.graph_edge_id, randomUUID()),
                    r.relation_type = coalesce(r.relation_type, trim(derived_relation_type)),
                    r.space_id = $space_id
                RETURN count(r) as enriched_count
                """

                edge_result = await session.run(
                    edge_query,
                    space_id=space_id,
                )
                edge_record = await edge_result.single()
                edges_enriched = edge_record["enriched_count"] if edge_record else 0

                return {
                    "nodes_enriched": nodes_enriched,
                    "edges_enriched": edges_enriched,
                }

        except Exception as e:
            logger.error(f"Failed to enrich LightRAG graph data: {e}")
            raise
        finally:
            await driver.close()

    @staticmethod
    def _parse_source_ids(source_id_str: str | None) -> list[str]:
        """Parse LightRAG source_id field.

        Format: "chunk-abc<|GRAPH_FIELD_SEP|>chunk-xyz"
        Returns: ["chunk-abc", "chunk-xyz"]
        """
        if not source_id_str:
            return []

        separator = "<|GRAPH_FIELD_SEP|>"
        return [s.strip() for s in source_id_str.split(separator) if s.strip()]

    @staticmethod
    async def _fetch_document_titles(records: list[list[Any]], session) -> dict[int, str]:
        """Fetch document titles for all document_ids in the graph result.

        Args:
            records: Neo4j path records
            session: SQLAlchemy session

        Returns:
            Dictionary mapping document_id -> document title
        """
        if not session:
            return {}

        # Collect all document_ids from the paths
        doc_ids = set()
        for (path,) in records:
            if path is None:
                continue

            # Handle single node case
            if not hasattr(path, "nodes"):
                if hasattr(path, "get") and path.get("document_id"):
                    doc_ids.add(path.get("document_id"))
                continue

            # Handle path with nodes
            if hasattr(path, "nodes"):
                for node in path.nodes:
                    if node.get("document_id"):
                        doc_ids.add(node.get("document_id"))

        if not doc_ids:
            return {}

        # Batch query document titles
        try:
            from sqlmodel import select

            from langflow.services.database.models.document import Document

            stmt = select(Document.id, Document.title).where(Document.id.in_(doc_ids))
            result = await session.execute(stmt)
            return {row[0]: row[1] for row in result.all()}
        except Exception as e:
            logger.warning(f"Failed to fetch document titles: {e}")
            return {}

    def _build_result_from_paths(
        self, records: list[list[Any]], doc_titles: dict[int, str] | None = None
    ) -> GraphQueryResult:
        nodes_by_id: dict[str, GraphNode] = {}
        edges_by_id: dict[str, GraphEdge] = {}
        raw_paths: list[dict[str, Any]] = []
        doc_titles = doc_titles or {}

        for (path,) in records:
            if path is None:
                continue
            if not hasattr(path, "nodes") and not hasattr(path, "relationships"):
                node_id = path.get("graph_node_id") or path.element_id
                if node_id not in nodes_by_id:
                    doc_id = path.get("document_id")
                    # Parse source_chunks from source_id field
                    source_chunks = self._parse_source_ids(path.get("source_id"))
                    properties = path.get("properties") or {}
                    if source_chunks:
                        properties = {**properties, "source_chunks": source_chunks}

                    nodes_by_id[node_id] = GraphNode(
                        id=node_id,
                        name=path.get("name"),
                        entity_type=path.get("entity_type"),
                        description=path.get("description"),
                        aliases=path.get("aliases") or [],
                        properties=properties,
                        space_id=path.get("space_id"),
                        document_id=doc_id,
                        chunk_id=path.get("chunk_id"),
                        document_title=doc_titles.get(doc_id) if doc_id else None,
                    )
                raw_paths.append({"nodes": [node_id], "edges": []})
                continue

            path_nodes = []
            path_edges = []

            for node in path.nodes:
                node_id = node.get("graph_node_id") or node.element_id
                if node_id not in nodes_by_id:
                    doc_id = node.get("document_id")
                    # Parse source_chunks from source_id field
                    source_chunks = self._parse_source_ids(node.get("source_id"))
                    properties = node.get("properties") or {}
                    if source_chunks:
                        properties = {**properties, "source_chunks": source_chunks}

                    nodes_by_id[node_id] = GraphNode(
                        id=node_id,
                        name=node.get("name"),
                        entity_type=node.get("entity_type"),
                        description=node.get("description"),
                        aliases=node.get("aliases") or [],
                        properties=properties,
                        space_id=node.get("space_id"),
                        document_id=doc_id,
                        chunk_id=node.get("chunk_id"),
                        document_title=doc_titles.get(doc_id) if doc_id else None,
                    )
                path_nodes.append(node_id)

            for rel in path.relationships:
                rel_id = rel.get("graph_edge_id") or rel.element_id
                source_id = rel.start_node.get("graph_node_id") or rel.start_node.element_id
                target_id = rel.end_node.get("graph_node_id") or rel.end_node.element_id
                if rel_id not in edges_by_id:
                    edges_by_id[rel_id] = GraphEdge(
                        id=rel_id,
                        source=source_id,
                        target=target_id,
                        relation_type=rel.type,
                        description=rel.get("description"),
                        weight=rel.get("weight"),
                        properties=rel.get("properties") or {},
                    )
                path_edges.append(rel_id)

            raw_paths.append({
                "nodes": path_nodes,
                "edges": path_edges,
                "length": len(path.relationships),
            })

        return GraphQueryResult(
            nodes=list(nodes_by_id.values()),
            edges=list(edges_by_id.values()),
            raw_paths=raw_paths,
        )


_graph_service: Neo4jGraphService | None = None


def get_neo4j_graph_service() -> Neo4jGraphService:
    """Get or create a Neo4j graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = Neo4jGraphService()
    return _graph_service
