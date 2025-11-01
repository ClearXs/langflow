"""Streaming execution engine for coordinating real-time data flow.

This module provides the core engine for executing streaming components
and propagating data in real-time through the graph.
"""

import asyncio
from collections.abc import AsyncGenerator

from lfx.log.logger import logger
from lfx.schema import Data


class StreamingExecutor:
    """Coordinates streaming execution across graph vertices.

    This executor manages the lifecycle of streaming components and ensures
    proper data propagation to downstream vertices.
    """

    def __init__(self):
        """Initialize the streaming executor."""
        self._active_streams = {}
        self._should_stop = False

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
                    await self._propagate_to_downstream(data, downstream_vertices, graph)

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
                    await self._propagate_to_downstream(data, downstream_vertices, graph)

            else:
                # Not a streaming result, just yield it once
                yield result
                await self._propagate_to_downstream(result, downstream_vertices, graph)

            logger.info(f"Streaming completed for {vertex.display_name}")

        except Exception as e:
            logger.error(f"Streaming error in {vertex.display_name}: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def _propagate_to_downstream(self, data: Data, downstream_vertices: list, graph):
        """Propagate a single data item to all downstream vertices.

        This method passes a single Data object to downstream components.
        Components should handle both single Data and list[Data] inputs.

        Args:
            data: The data item to propagate
            downstream_vertices: List of downstream vertices
            graph: The graph instance
        """
        for downstream_vertex in downstream_vertices:
            try:
                logger.debug(f"Propagating data to {downstream_vertex.display_name}")
                # Set the input data for the downstream vertex (single Data)
                input_set = await self._set_vertex_input(downstream_vertex, data)

                if not input_set:
                    logger.warning(f"Could not set input for {downstream_vertex.display_name}, skipping")
                    continue

                # Trigger execution of downstream vertex using public build() method
                # Pass fallback_to_env_vars=False as default
                result = await downstream_vertex.build(fallback_to_env_vars=False)

                # If downstream has its own downstream vertices, propagate recursively
                if result:
                    next_downstream = graph.get_successors(downstream_vertex)
                    if next_downstream:
                        await self._propagate_to_downstream(result, next_downstream, graph)

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
            logger.info(f"[STREAMING] ✓ Set updated_raw_params=True")

            # Also set on custom_component if it exists
            if hasattr(vertex, "custom_component") and vertex.custom_component:
                if hasattr(vertex.custom_component, param_name_to_set):
                    setattr(vertex.custom_component, param_name_to_set, data)
                    logger.info(f"[STREAMING] ✓ Set custom_component.{param_name_to_set}")

            return True

        logger.warning(f"No suitable input parameter found for {vertex.display_name}")
        return False

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
