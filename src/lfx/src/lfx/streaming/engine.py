"""Streaming execution engine for coordinating real-time data flow.

This module provides the core engine for executing streaming components
and propagating data in real-time through the graph.
"""

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

from lfx.log.logger import logger
from lfx.schema import Data
from lfx.streaming.data_exchange_tracker import AggregatedExchangeTracker, DataExchangeTracker


class StreamingExecutor:
    """Coordinates streaming execution across graph vertices.

    This executor manages the lifecycle of streaming components and ensures
    proper data propagation to downstream vertices.
    """

    def __init__(self, transaction_id: UUID | None = None, db_session=None, enable_tracking: bool = True):
        """Initialize the streaming executor.

        Args:
            transaction_id: Optional transaction ID for data exchange tracking
            db_session: Optional database session for persisting tracking data
            enable_tracking: Whether to enable data exchange tracking
        """
        self._active_streams = {}
        self._should_stop = False
        self._transaction_id = transaction_id
        self._db_session = db_session
        self._enable_tracking = enable_tracking
        self._data_exchange_tracker: DataExchangeTracker | None = None
        self._aggregated_trackers: dict[str, AggregatedExchangeTracker] = {}  # vertex_id -> tracker

        # Initialize tracker if tracking is enabled
        if self._enable_tracking and self._transaction_id:
            self._data_exchange_tracker = DataExchangeTracker(transaction_id=self._transaction_id)

    async def execute_streaming_vertex(self, vertex, downstream_vertices: list, graph) -> AsyncGenerator[Data, None]:
        """Execute a streaming vertex and propagate data to downstream vertices.

        Args:
            vertex: The streaming vertex to execute
            downstream_vertices: List of downstream vertices to propagate data to
            graph: The graph instance for accessing execution context

        Yields:
            Data objects from the streaming vertex
        """
        from collections.abc import Generator

        try:
            logger.info(f"Starting streaming execution for {vertex.display_name}")

            # Build the streaming vertex using the public build() method
            result = await vertex.build()

            # If result is a dict, check if it contains a Generator
            # (Component.build_results() returns a dict with outputs)
            if isinstance(result, dict):
                # Try to find a Generator in the dict values
                generator_found = None
                for key, value in result.items():
                    if isinstance(value, (Generator, AsyncGenerator)):
                        generator_found = value
                        break

                if generator_found is not None:
                    result = generator_found

            # Check if result is an async generator
            if isinstance(result, AsyncGenerator):
                async for data in result:
                    # Check both executor and vertex stop signals
                    if self._should_stop or (hasattr(vertex, "_should_stop") and vertex._should_stop):
                        logger.info(f"Stopping streaming for {vertex.display_name}")
                        # Propagate stop signal to vertex component
                        if hasattr(vertex, "custom_component") and hasattr(vertex.custom_component, "_should_stop"):
                            vertex.custom_component._should_stop = True
                        break

                    # Yield data to track progress
                    yield data

                    # Propagate to downstream vertices
                    await self._propagate_to_downstream(data, downstream_vertices, graph, source_vertex=vertex)

            # Check if result is a sync generator - convert to async
            elif isinstance(result, Generator):
                logger.warning(
                    f"Sync generator detected in {vertex.display_name}, consider converting to async for better performance"
                )
                async for data in self._sync_generator_to_async(result):
                    # Check both executor and vertex stop signals
                    if self._should_stop or (hasattr(vertex, "_should_stop") and vertex._should_stop):
                        logger.info(f"Stopping streaming for {vertex.display_name}")
                        # Propagate stop signal to vertex component
                        if hasattr(vertex, "custom_component") and hasattr(vertex.custom_component, "_should_stop"):
                            vertex.custom_component._should_stop = True
                        break

                    # Yield data to track progress
                    yield data

                    # Propagate to downstream vertices
                    await self._propagate_to_downstream(data, downstream_vertices, graph, source_vertex=vertex)

            else:
                # Not a streaming result, extract Data objects and propagate
                logger.debug(f"Non-streaming result from {vertex.display_name}, type: {type(result)}")

                # Extract Data objects from result dict
                data_to_propagate = []
                if isinstance(result, dict):
                    # Try to find Data objects in common result keys
                    for key in ["data", "result", "output", "message"]:
                        if key in result:
                            value = result[key]
                            if isinstance(value, list):
                                # Filter for Data objects
                                data_to_propagate = [item for item in value if hasattr(item, "__class__") and item.__class__.__name__ == "Data"]
                            elif hasattr(value, "__class__") and value.__class__.__name__ == "Data":
                                data_to_propagate = [value]
                            if data_to_propagate:
                                logger.debug(f"Extracted {len(data_to_propagate)} Data objects from '{key}'")
                                break

                # If we found Data objects, propagate each one
                if data_to_propagate:
                    for data in data_to_propagate:
                        yield data
                        await self._propagate_to_downstream(data, downstream_vertices, graph, source_vertex=vertex)
                else:
                    # No Data objects found, yield the raw result (for non-Data outputs)
                    logger.debug("No Data objects found in result, yielding raw result")
                    yield result

            logger.info(f"Streaming completed for {vertex.display_name}")

        except Exception as e:
            logger.error(f"Streaming error in {vertex.display_name}: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def _propagate_to_downstream(self, data: Data, downstream_vertices: list, graph, source_vertex=None):
        """Propagate a single data item to all downstream vertices.

        This method passes a single Data object to downstream components.
        Components should handle both single Data and list[Data] inputs.

        Args:
            data: The data item to propagate
            downstream_vertices: List of downstream vertices
            graph: The graph instance
            source_vertex: Optional source vertex for tracking
        """
        for downstream_vertex in downstream_vertices:
            try:
                logger.debug(f"Propagating data to {downstream_vertex.display_name}")

                # Track data exchange if enabled
                if self._enable_tracking and source_vertex:
                    await self._track_data_exchange(source_vertex, downstream_vertex, data)

                # Set the input data for the downstream vertex (single Data)
                input_set = await self._set_vertex_input(downstream_vertex, data)

                if not input_set:
                    logger.warning(f"Could not set input for {downstream_vertex.display_name}, skipping")
                    continue

                # Trigger execution of downstream vertex using public build() method
                # Pass fallback_to_env_vars=False as default
                result = await downstream_vertex.build(fallback_to_env_vars=False)

                # Extract actual data from build result
                # Build result is typically {'data': [Data(...)], 'artifacts': {}}
                # We need to extract the Data objects for further propagation
                extracted_data = None
                if result:
                    if isinstance(result, dict):
                        logger.debug(f"Result is dict with keys: {list(result.keys())}")
                        # Try to extract data from common result keys
                        for key in ["data", "result", "output", "message"]:
                            if key in result:
                                extracted_value = result[key]
                                logger.debug(f"Found '{key}' in result, type: {type(extracted_value)}")

                                # Handle list of Data objects
                                if isinstance(extracted_value, list) and extracted_value:
                                    if hasattr(extracted_value[0], "__class__") and extracted_value[0].__class__.__name__ == "Data":
                                        # Use the first Data object for propagation
                                        extracted_data = extracted_value[0]
                                        logger.debug(f"Extracted Data object from list: {extracted_data}")
                                        break
                                # Handle single Data object
                                elif hasattr(extracted_value, "__class__") and extracted_value.__class__.__name__ == "Data":
                                    extracted_data = extracted_value
                                    logger.debug(f"Extracted single Data object: {extracted_data}")
                                    break
                    else:
                        # Result is already a Data object or compatible type
                        extracted_data = result

                # If downstream has its own downstream vertices, propagate recursively
                if extracted_data:
                    next_downstream = graph.get_successors(downstream_vertex)
                    if next_downstream:
                        logger.debug(f"Propagating extracted data to {len(next_downstream)} downstream vertices")
                        await self._propagate_to_downstream(
                            extracted_data, next_downstream, graph, source_vertex=downstream_vertex
                        )
                else:
                    logger.debug(f"No data to propagate from {downstream_vertex.display_name}")

            except Exception as e:
                logger.error(f"Error propagating to {downstream_vertex.display_name}: {e}")
                import traceback

                traceback.print_exc()
                # Continue to next downstream vertex even if one fails

    async def _sync_generator_to_async(self, sync_gen):
        """Convert a synchronous generator to an async generator.

        This runs the sync generator in a thread pool to avoid blocking the event loop.

        Args:
            sync_gen: A synchronous generator

        Yields:
            Items from the synchronous generator
        """
        import asyncio

        def get_next_item(gen):
            """Get the next item from a synchronous generator."""
            try:
                return next(gen), False
            except StopIteration:
                return None, True

        while True:
            # Check stop signal before fetching next item
            if self._should_stop:
                logger.debug("Stop signal detected, closing sync generator")
                # Try to close the generator gracefully
                try:
                    sync_gen.close()
                except Exception:
                    pass
                break

            try:
                # Run next() in a thread pool with timeout to allow cancellation
                item, done = await asyncio.wait_for(asyncio.to_thread(get_next_item, sync_gen), timeout=2.0)

                if done:
                    break

                # Yield the item asynchronously
                yield item

            except asyncio.TimeoutError:
                # Timeout waiting for next item, check stop signal and retry
                if self._should_stop:
                    logger.debug("Stop signal detected during timeout, closing sync generator")
                    try:
                        sync_gen.close()
                    except Exception:
                        pass
                    break
                # If not stopped, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error in sync generator conversion: {e}")
                try:
                    sync_gen.close()
                except Exception:
                    pass
                raise

            # Give other tasks a chance to run
            await asyncio.sleep(0)

    async def _set_vertex_input(self, vertex, data: Data) -> bool:
        """Set input data for a vertex, forcefully overriding edge-connected Vertex objects.

        In streaming execution, we need to replace the upstream Vertex reference
        with actual Data objects. This bypasses the normal Vertex protection in
        update_raw_params() which prevents overwriting Vertex objects.

        Args:
            vertex: The vertex to set input for
            data: The data to set as input

        Returns:
            True if input was set successfully, False otherwise
        """
        common_names = ["data_input", "input_data", "data", "input_value", "message"]

        # Try to find the parameter name that should receive the data
        param_name_to_set = None

        # Strategy 1: Check if parameter exists in vertex.params
        if hasattr(vertex, "params"):
            for param_name in common_names:
                if param_name in vertex.params:
                    param_name_to_set = param_name
                    break

        # Strategy 2: Find any parameter that accepts Data/Message type
        if not param_name_to_set and hasattr(vertex, "params"):
            for param_name, param in vertex.params.items():
                if hasattr(param, "input_types"):
                    input_types = param.input_types or []
                    if "Data" in input_types or "Message" in input_types:
                        param_name_to_set = param_name
                        break

        # If we found a parameter, forcefully set it
        if param_name_to_set:
            logger.info(f"[STREAMING] Setting {param_name_to_set} for {vertex.display_name}")
            logger.info(f"[STREAMING] Data type: {type(data).__name__}, Data value: {data}")

            # Log what was there before
            if hasattr(vertex, "raw_params") and param_name_to_set in vertex.raw_params:
                old_value = vertex.raw_params[param_name_to_set]
                logger.info(f"[STREAMING] OLD raw_params[{param_name_to_set}] type: {type(old_value).__name__}")

            # Forcefully update both raw_params and params, bypassing Vertex protection
            if hasattr(vertex, "raw_params"):
                vertex.raw_params[param_name_to_set] = data
                logger.info(f"[STREAMING] ✓ Updated raw_params[{param_name_to_set}]")
            if hasattr(vertex, "params"):
                vertex.params[param_name_to_set] = data
                logger.info(f"[STREAMING] ✓ Updated params[{param_name_to_set}]")

            # Mark that raw_params have been updated to prevent re-processing
            vertex.updated_raw_params = True
            logger.info("[STREAMING] ✓ Set updated_raw_params=True")

            # Also set on custom_component if it exists
            if hasattr(vertex, "custom_component") and vertex.custom_component:
                if hasattr(vertex.custom_component, param_name_to_set):
                    setattr(vertex.custom_component, param_name_to_set, data)
                    logger.info(f"[STREAMING] ✓ Set custom_component.{param_name_to_set}")

            return True

        logger.warning(f"No suitable input parameter found for {vertex.display_name}")
        return False

    async def _track_data_exchange(self, source_vertex, target_vertex, data: Data):
        """Track a data exchange between two vertices.

        Args:
            source_vertex: The source vertex
            target_vertex: The target vertex
            data: The data being exchanged
        """
        if not self._data_exchange_tracker:
            return

        # Determine if source is a high-frequency streaming component
        is_high_frequency = self._is_high_frequency_component(source_vertex)

        if is_high_frequency:
            # Use aggregated tracker for high-frequency components
            source_id = getattr(source_vertex, "id", source_vertex.display_name)

            if source_id not in self._aggregated_trackers:
                self._aggregated_trackers[source_id] = AggregatedExchangeTracker(
                    transaction_id=self._transaction_id, window_seconds=60
                )

            tracker = self._aggregated_trackers[source_id]
            tracker.record_exchange(
                source_vertex_id=source_id,
                source_vertex_name=source_vertex.display_name,
                target_vertex_id=getattr(target_vertex, "id", target_vertex.display_name),
                target_vertex_name=target_vertex.display_name,
                data=data,
                exchange_type="aggregated",
            )

            # Check if window should be flushed
            if tracker.should_flush() and self._db_session:
                await tracker.flush_to_database(self._db_session)
        else:
            # Use regular tracker for normal components
            self._data_exchange_tracker.record_exchange(
                source_vertex_id=getattr(source_vertex, "id", source_vertex.display_name),
                source_vertex_name=source_vertex.display_name,
                target_vertex_id=getattr(target_vertex, "id", target_vertex.display_name),
                target_vertex_name=target_vertex.display_name,
                data=data,
                exchange_type="direct",
            )

    def _is_high_frequency_component(self, vertex) -> bool:
        """Check if a vertex is a high-frequency streaming component.

        Args:
            vertex: The vertex to check

        Returns:
            True if vertex is high-frequency (kafka, cdc, etc.)
        """
        # List of high-frequency component types
        high_frequency_types = ["kafka_input", "cdc_input", "stream_input", "real_time_input"]

        # Check vertex type/name
        vertex_type = getattr(vertex, "vertex_type", "").lower()
        vertex_name = getattr(vertex, "display_name", "").lower()

        return any(hf_type in vertex_type or hf_type in vertex_name for hf_type in high_frequency_types)

    async def flush_tracking_data(self) -> dict[str, int]:
        """Flush all pending tracking data to the database.

        Returns:
            Dict with flush statistics (regular_count, aggregated_count)
        """
        stats = {"regular_count": 0, "aggregated_count": 0}

        if not self._enable_tracking or not self._db_session:
            return stats

        # Flush regular tracker
        if self._data_exchange_tracker:
            stats["regular_count"] = await self._data_exchange_tracker.flush_to_database(self._db_session)

        # Flush all aggregated trackers
        for tracker in self._aggregated_trackers.values():
            count = await tracker.flush_to_database(self._db_session)
            stats["aggregated_count"] += count

        return stats

    def get_tracking_summary(self) -> dict:
        """Get summary of tracked data exchanges.

        Returns:
            Dict with tracking summary
        """
        if not self._data_exchange_tracker:
            return {"enabled": False}

        return {
            "enabled": True,
            "exchange_count": self._data_exchange_tracker.get_exchange_count(),
            "downstream_vertices": self._data_exchange_tracker.get_downstream_vertices(),
            "aggregated_trackers": len(self._aggregated_trackers),
        }

    def stop(self):
        """Stop all active streaming executions."""
        self._should_stop = True
        logger.info("Stopping all streaming executions")


class StreamCoordinator:
    """Coordinates multiple streaming vertices in a graph.

    This coordinator manages the execution order and data flow between
    multiple streaming components.
    """

    def __init__(self, graph):
        """Initialize the stream coordinator.

        Args:
            graph: The graph instance to coordinate streams for
        """
        self.graph = graph
        self.executor = StreamingExecutor()

    async def coordinate_streams(self):
        """Coordinate execution of all streaming vertices in the graph."""
        streaming_vertices = self._identify_streaming_vertices()

        if not streaming_vertices:
            logger.info("No streaming vertices found in graph")
            return

        logger.info(f"Found {len(streaming_vertices)} streaming vertices")

        # Execute all streaming vertices concurrently
        tasks = []
        for vertex in streaming_vertices:
            downstream = self._get_downstream_vertices(vertex)
            task = self.executor.execute_streaming_vertex(vertex, downstream, self.graph)
            tasks.append(task)

        # Wait for all streaming tasks
        await asyncio.gather(*tasks)

    def _identify_streaming_vertices(self) -> list:
        """Identify all streaming vertices in the graph.

        Returns:
            List of vertices that are streaming components
        """
        streaming_vertices = []
        for vertex in self.graph.vertices:
            if getattr(vertex, "is_streaming", False) or getattr(
                vertex.custom_component, "is_streaming_component", False
            ):
                streaming_vertices.append(vertex)
        return streaming_vertices

    def _get_downstream_vertices(self, vertex) -> list:
        """Get all downstream vertices for a given vertex.

        Args:
            vertex: The vertex to get downstream vertices for

        Returns:
            List of downstream vertices (direct successors only)
        """
        return self.graph.get_successors(vertex)
