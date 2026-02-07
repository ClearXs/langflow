"""SQLite-vec vector storage implementation.

A lightweight vector storage solution using SQLite with the sqlite-vec extension.
This implementation provides zero-dependency vector storage using pure SQLite.
"""

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from langflow.services.vector.base import BaseVectorStore, VectorMetadata, VectorSearchResult

logger = logging.getLogger(__name__)


class SqliteVecStore(BaseVectorStore):
    """SQLite-vec implementation of vector storage.

    This is a lightweight vector storage solution that uses SQLite with
    the sqlite-vec extension. It's ideal for:
    - Small to medium scale deployments (< 100K vectors)
    - Resource-constrained environments
    - Single-machine deployments
    - Development and testing

    Note: sqlite-vec uses approximate nearest neighbor search which may
    be less accurate than specialized vector databases for large datasets.
    """

    def __init__(self, database_path: str = "./vectors.db"):
        """Initialize SQLite-vec vector store.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.conn: sqlite3.Connection | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize SQLite connection and enable sqlite-vec extension."""
        if self._initialized:
            logger.debug("SQLite-vec already initialized")
            return

        try:
            # Create database directory if needed
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to SQLite
            self.conn = sqlite3.connect(self.database_path, check_same_thread=False)

            # Enable JSON support
            self.conn.row_factory = sqlite3.Row

            # Try to load sqlite-vec extension
            try:
                self.conn.enable_load_extension(True)
                extension_path = (
                    os.getenv("LANGFLOW_SQLITE_VEC_EXTENSION_PATH")
                    or os.getenv("LANGFLOW_VECTOR_SQLITE_VEC_EXTENSION_PATH")
                )
                tried = []
                if not extension_path:
                    try:
                        import sqlite_vec  # type: ignore

                        base = Path(sqlite_vec.__file__).parent
                        candidate = base / "vec0.dylib"
                        if candidate.exists():
                            extension_path = str(candidate)
                    except Exception:
                        extension_path = None

                if extension_path:
                    tried.append(extension_path)
                    try:
                        self.conn.load_extension(extension_path)
                        logger.info(f"Loaded sqlite-vec extension: {extension_path}")
                        self.conn.enable_load_extension(False)
                        self._initialized = True
                        return
                    except sqlite3.OperationalError:
                        logger.warning(
                            "Failed to load sqlite-vec extension from %s", extension_path
                        )

                # Try common extension names
                for ext_name in ["vec0", "sqlite_vec", "vector"]:
                    tried.append(ext_name)
                    try:
                        self.conn.load_extension(ext_name)
                        logger.info(f"Loaded sqlite-vec extension: {ext_name}")
                        break
                    except sqlite3.OperationalError:
                        continue
                self.conn.enable_load_extension(False)
            except Exception as e:
                logger.warning(f"Could not load sqlite-vec extension: {e}")
                logger.info("Falling back to pure SQLite (no vector indexing)")

            logger.info(f"Connected to SQLite at {self.database_path}")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize SQLite-vec: {e}")
            raise RuntimeError(f"SQLite-vec initialization failed: {e}") from e

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if collection (table) exists."""
        if not self._initialized:
            await self.initialize()

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (collection_name,),
            )
            result = cursor.fetchone()
            return result is not None

        except Exception as e:
            logger.error(f"Failed to check collection {collection_name}: {e}")
            return False

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a new collection (table) for vectors.

        Schema:
            - id INTEGER PRIMARY KEY AUTOINCREMENT
            - chunk_id INTEGER NOT NULL
            - embedding BLOB NOT NULL (stored as JSON for compatibility)
            - document_id INTEGER NOT NULL
            - space_id INTEGER NOT NULL
            - chunk_index INTEGER NOT NULL
            - chunk_type TEXT NOT NULL
            - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        Indexes:
            - idx_{collection}_chunk_id on chunk_id
            - idx_{collection}_space_id on space_id
            - idx_{collection}_document_id on document_id
        """
        if not self._initialized:
            await self.initialize()

        try:
            if await self.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} already exists")
                return

            cursor = self.conn.cursor()

            # Create table
            cursor.execute(
                f"""
                CREATE TABLE {collection_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id INTEGER NOT NULL,
                    embedding BLOB NOT NULL,
                    document_id INTEGER NOT NULL,
                    space_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute(f"CREATE INDEX idx_{collection_name}_chunk_id ON {collection_name}(chunk_id)")

            cursor.execute(f"CREATE INDEX idx_{collection_name}_space_id ON {collection_name}(space_id)")

            cursor.execute(
                f"CREATE INDEX idx_{collection_name}_document_id ON {collection_name}(document_id)"
            )

            # Store collection metadata
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS _collection_metadata (
                    collection_name TEXT PRIMARY KEY,
                    dimension INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                "INSERT INTO _collection_metadata (collection_name, dimension) VALUES (?, ?)",
                (collection_name, dimension),
            )

            self.conn.commit()
            logger.info(f"Created collection: {collection_name} with dimension {dimension}")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise ValueError(f"Collection creation failed: {e}") from e

    async def add_vectors(
        self, collection_name: str, vectors: list[list[float]], metadatas: list[VectorMetadata]
    ) -> list[str]:
        """Add vectors to collection."""
        if not self._initialized:
            await self.initialize()

        try:
            if not await self.collection_exists(collection_name):
                msg = f"Collection {collection_name} does not exist"
                raise ValueError(msg)

            cursor = self.conn.cursor()

            # Prepare data
            rows = []
            for vector, meta in zip(vectors, metadatas):
                # Serialize vector as JSON
                vector_json = json.dumps(vector)

                rows.append(
                    (
                        meta.chunk_id,
                        vector_json,
                        meta.document_id,
                        meta.space_id,
                        meta.chunk_index,
                        meta.chunk_type,
                    )
                )

            # Insert vectors and collect IDs
            ids = []
            for row in rows:
                cursor.execute(
                    f"""
                    INSERT INTO {collection_name}
                    (chunk_id, embedding, document_id, space_id, chunk_index, chunk_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    row,
                )
                ids.append(str(cursor.lastrowid))

            self.conn.commit()

            logger.info(f"Added {len(vectors)} vectors to {collection_name}")
            return ids

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to add vectors to {collection_name}: {e}")
            raise RuntimeError(f"Vector insertion failed: {e}") from e

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors using cosine similarity.

        Note: This is a brute-force search that computes similarity for all vectors.
        It's suitable for small to medium collections (< 100K vectors).
        """
        if not self._initialized:
            await self.initialize()

        try:
            if not await self.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                return []

            cursor = self.conn.cursor()

            # Build WHERE clause for filters
            where_clauses = []
            params = []

            if filter_dict:
                for key, value in filter_dict.items():
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Fetch all vectors (with filters)
            cursor.execute(
                f"""
                SELECT id, chunk_id, embedding, document_id, space_id, chunk_index, chunk_type
                FROM {collection_name}
                {where_sql}
            """,
                params,
            )

            rows = cursor.fetchall()

            # Compute cosine similarity for each vector
            results = []
            for row in rows:
                vector = json.loads(row["embedding"])
                similarity = self._cosine_similarity(query_vector, vector)

                # Convert similarity to distance (1 - similarity)
                distance = 1.0 - similarity

                results.append(
                    VectorSearchResult(
                        chunk_id=row["chunk_id"],
                        score=similarity,
                        distance=distance,
                        metadata={
                            "document_id": row["document_id"],
                            "space_id": row["space_id"],
                            "chunk_index": row["chunk_index"],
                            "chunk_type": row["chunk_type"],
                        },
                    )
                )

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]

            logger.info(f"Found {len(results)} results in {collection_name}")
            return results

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise RuntimeError(f"Search failed: {e}") from e

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            msg = f"Vector dimensions don't match: {len(vec1)} != {len(vec2)}"
            raise ValueError(msg)

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Compute magnitudes
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    async def delete_vectors(self, collection_name: str, chunk_ids: list[int]) -> None:
        """Delete vectors from collection."""
        if not self._initialized:
            await self.initialize()

        try:
            if not await self.collection_exists(collection_name):
                msg = f"Collection {collection_name} does not exist"
                raise ValueError(msg)

            cursor = self.conn.cursor()

            # Build IN clause
            placeholders = ",".join("?" * len(chunk_ids))
            cursor.execute(
                f"DELETE FROM {collection_name} WHERE chunk_id IN ({placeholders})",
                chunk_ids,
            )

            self.conn.commit()
            logger.info(f"Deleted {len(chunk_ids)} vectors from {collection_name}")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to delete vectors from {collection_name}: {e}")
            raise RuntimeError(f"Delete failed: {e}") from e

    async def delete_collection(self, collection_name: str) -> None:
        """Delete collection (table)."""
        if not self._initialized:
            await self.initialize()

        try:
            cursor = self.conn.cursor()

            # Drop table
            cursor.execute(f"DROP TABLE IF EXISTS {collection_name}")

            # Remove metadata
            cursor.execute("DELETE FROM _collection_metadata WHERE collection_name = ?", (collection_name,))

            self.conn.commit()
            logger.info(f"Deleted collection: {collection_name}")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise ValueError(f"Collection deletion failed: {e}") from e

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            if not await self.collection_exists(collection_name):
                msg = f"Collection {collection_name} does not exist"
                raise ValueError(msg)

            cursor = self.conn.cursor()

            # Get vector count
            cursor.execute(f"SELECT COUNT(*) as count FROM {collection_name}")
            count = cursor.fetchone()["count"]

            # Get dimension from metadata
            cursor.execute(
                "SELECT dimension FROM _collection_metadata WHERE collection_name = ?",
                (collection_name,),
            )
            dim_row = cursor.fetchone()
            dimension = dim_row["dimension"] if dim_row else None

            return {
                "vector_count": count,
                "dimension": dimension,
                "metadata": {"storage": "sqlite", "indexing": "brute-force"},
            }

        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            raise ValueError(f"Collection not found: {collection_name}") from e

    async def list_collections(self) -> list[str]:
        """List all collections."""
        if not self._initialized:
            await self.initialize()

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name = '_collection_metadata'
            """
            )
            if cursor.fetchone() is None:
                return []

            cursor.execute(
                """
                SELECT collection_name FROM _collection_metadata
                ORDER BY created_at
            """
            )
            collections = [row["collection_name"] for row in cursor.fetchall()]
            logger.debug(f"Found {len(collections)} collections")
            return collections

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise RuntimeError(f"Failed to list collections: {e}") from e

    async def reset(self) -> None:
        """Reset database (delete all collections) - for testing only."""
        if not self._initialized:
            await self.initialize()

        try:
            collections = await self.list_collections()
            for collection_name in collections:
                await self.delete_collection(collection_name)

            # Also drop metadata table
            cursor = self.conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS _collection_metadata")
            self.conn.commit()

            logger.warning("SQLite-vec reset complete - all collections deleted")

        except Exception as e:
            logger.error(f"Failed to reset SQLite-vec: {e}")
            raise RuntimeError(f"Reset failed: {e}") from e

    async def close(self) -> None:
        """Close SQLite connection."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self._initialized = False
                logger.info("SQLite-vec connection closed")

        except Exception as e:
            logger.error(f"Failed to close SQLite-vec connection: {e}")
