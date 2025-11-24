"""Database indexes for TransactionTable to optimize execution log queries.

This module provides utility functions to create database indexes that
improve query performance for the execution logs API endpoints.
"""

from loguru import logger
from sqlmodel import create_engine, text

from langflow.services.deps import get_settings_service


def create_execution_log_indexes():
    """Create database indexes to optimize execution log queries.

    Creates the following indexes:
    1. Index on flow_id for fast flow-specific queries
    2. Composite index on (flow_id, status) for filtered status queries
    3. Composite index on (flow_id, timestamp) for time-based queries
    4. Index on flow_id for transaction lookup
    5. JSON path indexes for metadata filtering (if supported by database)

    Note: This should be called during application startup or migrations.
    """
    settings_service = get_settings_service()
    database_url = settings_service.settings.database_url

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Create index for flow-specific queries
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_transaction_flow_id
                ON transaction(flow_id)
            """)
            )

            # Create composite index for flow + status filtering
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_transaction_flow_status
                ON transaction(flow_id, status)
            """)
            )

            # Create composite index for flow + time ordering
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_transaction_flow_timestamp
                ON transaction(flow_id, timestamp DESC)
            """)
            )

            # Create index for transaction lookup by flow and vertex
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_transaction_flow_vertex
                ON transaction(flow_id, vertex_id)
            """)
            )

            # Check if database supports JSON indexes
            db_type = _get_database_type(database_url)
            if db_type == "postgresql":
                # PostgreSQL JSON path indexes
                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_transaction_inputs_component_type
                    ON transaction USING GIN ((inputs->'_metadata'->>'component_type'))
                """)
                )

                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_transaction_outputs_metadata
                    ON transaction USING GIN (outputs)
                """)
                )

                logger.info("Created PostgreSQL JSON indexes for transaction metadata")

            elif db_type == "sqlite":
                # SQLite JSON path indexes (SQLite 3.38+)
                try:
                    conn.execute(
                        text("""
                        CREATE INDEX IF NOT EXISTS idx_transaction_inputs_component_type
                        ON transaction ((json_extract(inputs, '$._metadata.component_type')))
                    """)
                    )

                    logger.info("Created SQLite JSON indexes for transaction metadata")

                except Exception as e:
                    logger.warning(f"Could not create SQLite JSON indexes (may need newer SQLite version): {e}")

            conn.commit()

        logger.info("Successfully created execution log database indexes")

    except Exception as e:
        logger.error(f"Failed to create execution log indexes: {e}")
        # Don't raise exception to prevent app startup failure
        # Index creation can be retried later


def _get_database_type(database_url: str) -> str:
    """Determine database type from connection URL.

    Args:
        database_url: Database connection URL

    Returns:
        Database type: 'postgresql', 'sqlite', or 'unknown'
    """
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        return "postgresql"
    if database_url.startswith("sqlite://"):
        return "sqlite"
    return "unknown"


def drop_execution_log_indexes():
    """Drop all execution log indexes (useful for testing or migrations).

    Note: This should be used with care as it will remove performance optimizations.
    """
    settings_service = get_settings_service()
    database_url = settings_service.settings.database_url

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Drop indexes if they exist
            indexes_to_drop = [
                "idx_transaction_flow_id",
                "idx_transaction_flow_status",
                "idx_transaction_flow_timestamp",
                "idx_transaction_flow_vertex",
                "idx_transaction_inputs_component_type",
                "idx_transaction_outputs_metadata",
            ]

            for index_name in indexes_to_drop:
                try:
                    conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                    logger.info(f"Dropped index: {index_name}")
                except Exception as e:
                    logger.warning(f"Could not drop index {index_name}: {e}")

            conn.commit()

        logger.info("Successfully dropped execution log database indexes")

    except Exception as e:
        logger.error(f"Failed to drop execution log indexes: {e}")
