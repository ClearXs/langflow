"""Data exchange tracking for streaming execution.

This module provides utilities to track data exchanges between components
during streaming execution.
"""

import sys
from datetime import datetime, timezone
from uuid import UUID

from lfx.log.logger import logger
from lfx.schema import Data


class DataExchangeTracker:
    """Tracks data exchanges between components during execution."""

    def __init__(self, transaction_id: UUID | None = None):
        """Initialize the data exchange tracker.

        Args:
            transaction_id: The transaction ID for this execution
        """
        self.transaction_id = transaction_id
        self._exchange_buffer: list[dict] = []
        self._exchange_count = 0
        self._downstream_vertices_set: set[str] = set()

    def record_exchange(
        self,
        source_vertex_id: str,
        source_vertex_name: str,
        target_vertex_id: str,
        target_vertex_name: str,
        data: Data,
        exchange_type: str = "direct",
    ) -> None:
        """Record a single data exchange.

        Args:
            source_vertex_id: Source vertex ID
            source_vertex_name: Source vertex display name
            target_vertex_id: Target vertex ID
            target_vertex_name: Target vertex display name
            data: The data being exchanged
            exchange_type: Type of exchange (direct, broadcast, conditional, aggregated)
        """
        # Calculate data size
        data_size = self._calculate_data_size(data)

        # Serialize data sample
        data_sample = self._serialize_data_sample(data)

        # Record exchange metadata
        exchange_record = {
            "timestamp": datetime.now(timezone.utc),
            "transaction_id": self.transaction_id,
            "source_vertex_id": source_vertex_id,
            "target_vertex_id": target_vertex_id,
            "exchange_type": exchange_type,
            "data_type": type(data).__name__,
            "data_size": data_size,
            "data_sample": data_sample,
            "exchange_metadata": {
                "source_component": source_vertex_name,
                "target_component": target_vertex_name,
            },
        }

        self._exchange_buffer.append(exchange_record)
        self._exchange_count += 1
        self._downstream_vertices_set.add(target_vertex_id)

        logger.debug(
            f"Recorded exchange: {source_vertex_name} -> {target_vertex_name}, size: {data_size} bytes, type: {exchange_type}"
        )

    def _calculate_data_size(self, data: Data) -> int:
        """Calculate the approximate size of data in bytes.

        Args:
            data: The data object

        Returns:
            Approximate size in bytes
        """
        try:
            # Try to get size using sys.getsizeof
            return sys.getsizeof(data)
        except Exception:
            # Fallback: estimate based on string representation
            try:
                return len(str(data))
            except Exception:
                return 0

    def _serialize_data_sample(self, data: Data) -> dict:
        """Serialize a sample of the data for storage.

        Args:
            data: The data object

        Returns:
            Dict containing sampled data
        """
        try:
            # Import serialization utilities from langflow
            from langflow.serialization.serialization import (
                get_max_items_length,
                get_max_text_length,
                serialize,
            )

            # Convert Data to dict for serialization
            if hasattr(data, "model_dump"):
                data_dict = data.model_dump()
            elif hasattr(data, "dict"):
                data_dict = data.dict()
            elif hasattr(data, "__dict__"):
                data_dict = data.__dict__
            else:
                data_dict = {"value": str(data)}

            # Serialize with size limits
            return serialize(data_dict, max_length=get_max_text_length(), max_items=get_max_items_length())

        except Exception as e:
            logger.warning(f"Failed to serialize data sample: {e}")
            return {"error": "Serialization failed", "type": type(data).__name__}

    async def flush_to_database(self, db_session) -> int:
        """Flush buffered exchanges to the database.

        Args:
            db_session: Database session

        Returns:
            Number of records flushed
        """
        if not self._exchange_buffer:
            return 0

        try:
            from langflow.services.database.models.data_exchange import (
                DataExchangeBase,
                log_data_exchanges_bulk,
            )

            # Convert buffer to DataExchangeBase objects
            exchanges = [DataExchangeBase(**record) for record in self._exchange_buffer]

            # Bulk insert
            await log_data_exchanges_bulk(db_session, exchanges)

            count = len(self._exchange_buffer)
            logger.info(f"Flushed {count} data exchange records to database")

            # Clear buffer
            self._exchange_buffer.clear()

            return count

        except Exception as e:
            logger.error(f"Failed to flush data exchanges to database: {e}")
            # Don't raise - we don't want tracking failures to break execution
            return 0

    def get_exchange_count(self) -> int:
        """Get the total number of exchanges recorded.

        Returns:
            Number of exchanges
        """
        return self._exchange_count

    def get_downstream_vertices(self) -> list[str]:
        """Get list of unique downstream vertex IDs.

        Returns:
            List of vertex IDs
        """
        return list(self._downstream_vertices_set)

    def clear(self) -> None:
        """Clear all tracking data."""
        self._exchange_buffer.clear()
        self._exchange_count = 0
        self._downstream_vertices_set.clear()


class AggregatedExchangeTracker:
    """Tracks aggregated data exchanges for high-frequency streaming components.

    This tracker aggregates exchanges over time windows to reduce database load
    for components like kafka_input, cdc_input that produce many data exchanges.
    """

    def __init__(self, transaction_id: UUID | None = None, window_seconds: int = 60):
        """Initialize the aggregated exchange tracker.

        Args:
            transaction_id: The transaction ID for this execution
            window_seconds: Time window for aggregation in seconds
        """
        self.transaction_id = transaction_id
        self.window_seconds = window_seconds
        self._current_window_start: datetime | None = None
        self._current_window_data: dict[tuple[str, str], dict] = {}  # (source, target) -> stats

    def record_exchange(
        self,
        source_vertex_id: str,
        source_vertex_name: str,
        target_vertex_id: str,
        target_vertex_name: str,
        data: Data,
        exchange_type: str = "aggregated",
    ) -> None:
        """Record an exchange in the current aggregation window.

        Args:
            source_vertex_id: Source vertex ID
            source_vertex_name: Source vertex display name
            target_vertex_id: Target vertex ID
            target_vertex_name: Target vertex display name
            data: The data being exchanged
            exchange_type: Type of exchange
        """
        now = datetime.now(timezone.utc)

        # Initialize or reset window
        if self._current_window_start is None or (now - self._current_window_start).seconds >= self.window_seconds:
            self._current_window_start = now

        # Get or create aggregation entry
        key = (source_vertex_id, target_vertex_id)
        if key not in self._current_window_data:
            self._current_window_data[key] = {
                "count": 0,
                "total_size": 0,
                "data_types": set(),
                "source_name": source_vertex_name,
                "target_name": target_vertex_name,
            }

        # Update aggregation
        entry = self._current_window_data[key]
        entry["count"] += 1
        entry["total_size"] += self._calculate_data_size(data)
        entry["data_types"].add(type(data).__name__)

        logger.debug(
            f"Aggregated exchange: {source_vertex_name} -> {target_vertex_name}, count: {entry['count']}"
        )

    def _calculate_data_size(self, data: Data) -> int:
        """Calculate the approximate size of data in bytes.

        Args:
            data: The data object

        Returns:
            Approximate size in bytes
        """
        try:
            return sys.getsizeof(data)
        except Exception:
            try:
                return len(str(data))
            except Exception:
                return 0

    async def flush_to_database(self, db_session) -> int:
        """Flush aggregated exchanges to the database.

        Args:
            db_session: Database session

        Returns:
            Number of aggregated records flushed
        """
        if not self._current_window_data:
            return 0

        try:
            from langflow.services.database.models.data_exchange import (
                DataExchangeBase,
                log_data_exchanges_bulk,
            )

            # Convert aggregated data to DataExchangeBase objects
            exchanges = []
            for (source_id, target_id), stats in self._current_window_data.items():
                exchange = DataExchangeBase(
                    timestamp=self._current_window_start or datetime.now(timezone.utc),
                    transaction_id=self.transaction_id,
                    source_vertex_id=source_id,
                    target_vertex_id=target_id,
                    exchange_type="aggregated",
                    data_type=",".join(stats["data_types"]),
                    data_size=stats["total_size"],
                    data_sample={
                        "aggregated": True,
                        "count": stats["count"],
                        "avg_size": stats["total_size"] / stats["count"] if stats["count"] > 0 else 0,
                        "window_start": self._current_window_start.isoformat()
                        if self._current_window_start
                        else None,
                        "window_seconds": self.window_seconds,
                    },
                    exchange_metadata={
                        "source_component": stats["source_name"],
                        "target_component": stats["target_name"],
                    },
                )
                exchanges.append(exchange)

            # Bulk insert
            await log_data_exchanges_bulk(db_session, exchanges)

            count = len(exchanges)
            total_exchanges = sum(stats["count"] for stats in self._current_window_data.values())
            logger.info(f"Flushed {count} aggregated records ({total_exchanges} total exchanges) to database")

            # Clear current window
            self._current_window_data.clear()
            self._current_window_start = None

            return count

        except Exception as e:
            logger.error(f"Failed to flush aggregated data exchanges to database: {e}")
            return 0

    def should_flush(self) -> bool:
        """Check if the current window should be flushed.

        Returns:
            True if window duration has elapsed
        """
        if self._current_window_start is None:
            return False

        now = datetime.now(timezone.utc)
        return (now - self._current_window_start).seconds >= self.window_seconds

    def clear(self) -> None:
        """Clear all tracking data."""
        self._current_window_data.clear()
        self._current_window_start = None
