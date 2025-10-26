"""Utility functions for graph operations during component build configuration."""

import json
from typing import TYPE_CHECKING, Any

from lfx.log.logger import logger
from lfx.schema import Data

if TYPE_CHECKING:
    from lfx.graph.graph.base import Graph


def find_upstream_node_id(graph_data: dict, target_node_id: str, input_name: str) -> str | None:
    """Find the upstream node ID connected to a specific input.

    Supports multiple edge formats:
    1. React Flow format: {source, target, targetHandle}
    2. Langflow format: {source, target, data: {targetHandle: {fieldName}}}

    Args:
        graph_data: Flow graph data containing nodes and edges
        target_node_id: ID of the target node
        input_name: Name of the input field to find upstream connection for

    Returns:
        ID of the upstream node, or None if not found
    """
    edges = graph_data.get("edges", [])

    # Debug logging for troubleshooting
    if not edges:
        logger.warning(
            f"[GraphUtils] No edges found in graph_data. "
            f"Cannot find upstream node for '{target_node_id}' input '{input_name}'. "
            f"Available graph_data keys: {list(graph_data.keys())}"
        )
        return None

    logger.debug(f"[GraphUtils] Searching for upstream node: target='{target_node_id}', input='{input_name}'")
    logger.debug(f"[GraphUtils] Total edges to search: {len(edges)}")

    for edge in edges:
        # Check if this edge targets our node
        if edge.get("target") != target_node_id:
            continue

        # Try to extract target handle in multiple ways
        target_handle = None

        # Method 1: Try nested Langflow format first (most reliable)
        # Format: {data: {targetHandle: {fieldName: "data_input"}}}
        if "data" in edge:
            data_obj = edge.get("data", {})
            if isinstance(data_obj, dict):
                target_handle_data = data_obj.get("targetHandle", {})
                if isinstance(target_handle_data, dict):
                    target_handle = target_handle_data.get("fieldName")
                    logger.debug(f"[GraphUtils] Extracted fieldName from nested data: {target_handle}")

        # Method 2: Try to parse JSON string in targetHandle
        # Format: {targetHandle: '{"fieldName":"data_input",...}'}
        if not target_handle:
            top_level_handle = edge.get("targetHandle")
            if isinstance(top_level_handle, str):
                # Check if it's a JSON string (starts with '{' or '[')
                if top_level_handle.startswith("{") or top_level_handle.startswith("["):
                    try:
                        # Try to parse as JSON (handle the œ character encoding issue)
                        # Replace œ with " for proper JSON parsing
                        cleaned_json = top_level_handle.replace("œ", '"')
                        parsed = json.loads(cleaned_json)
                        if isinstance(parsed, dict):
                            target_handle = parsed.get("fieldName")
                            logger.debug(f"[GraphUtils] Extracted fieldName from JSON string: {target_handle}")
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.debug(f"[GraphUtils] Failed to parse targetHandle as JSON: {e}")
                else:
                    # It's a simple string, use it directly
                    target_handle = top_level_handle
                    logger.debug(f"[GraphUtils] Using simple string targetHandle: {target_handle}")

        logger.info(
            f"[GraphUtils] Examining edge: source={edge.get('source')}, "
            f"target={edge.get('target')}, targetHandle={target_handle}"
        )

        # Check if this edge connects to our input
        if target_handle == input_name:
            source_node_id = edge.get("source")
            logger.info(
                f"[GraphUtils] ✓ Found upstream node '{source_node_id}' "
                f"connected to '{target_node_id}' input '{input_name}'"
            )
            return source_node_id

    logger.warning(
        f"[GraphUtils] No upstream node found for '{target_node_id}' input '{input_name}'. "
        f"Checked {len(edges)} edges but none matched."
    )
    return None


async def execute_node_and_get_result(graph: "Graph", node_id: str, sample_size: int | None = None) -> list[Data]:
    """Execute a specific node in the graph and return its output data.

    Args:
        graph: The Graph instance
        node_id: ID of the node to execute
        sample_size: Optional limit on number of records to return

    Returns:
        List of Data objects from the node's execution

    Raises:
        ValueError: If node not found or execution fails
    """
    try:
        logger.debug(f"[GraphUtils] Executing node '{node_id}'")
        logger.debug(f"[GraphUtils] Graph type: {type(graph)}")
        logger.debug(f"[GraphUtils] Graph has vertices: {hasattr(graph, 'vertices')}")

        # Get the vertex for this node
        vertex = graph.get_vertex(node_id)
        if not vertex:
            msg = f"Node {node_id} not found in graph"
            logger.error(f"[GraphUtils] {msg}")
            logger.debug(
                f"[GraphUtils] Available vertices: {list(graph.vertices.keys()) if hasattr(graph, 'vertices') else 'N/A'}"
            )
            raise ValueError(msg)

        logger.debug(f"[GraphUtils] Executing vertex '{node_id}' of type '{vertex.vertex_type}'")

        # Execute the vertex (this runs all dependencies automatically)
        # Pass fallback_to_env_vars as it's required by vertex._build()
        result = await vertex.build(fallback_to_env_vars=True)

        logger.debug(f"[GraphUtils] Vertex execution completed, result type: {type(result)}")
        logger.debug(f"[GraphUtils] Result is Data: {isinstance(result, Data)}")
        logger.debug(f"[GraphUtils] Result is list: {isinstance(result, list)}")
        logger.debug(f"[GraphUtils] Result is dict: {isinstance(result, dict)}")

        # IMPORTANT: vertex.build() returns outputs as a dict keyed by output name
        # For example: {"data": [Data(...)]} instead of [Data(...)]
        # We need to unwrap this to get the actual data
        if isinstance(result, dict):
            logger.debug(f"[GraphUtils] Result is dict with keys: {list(result.keys())}")
            # Try to extract the actual data from the output dict
            # Common output names: "data", "output", "result"
            if len(result) == 1:
                # Single output - extract its value
                output_key = list(result.keys())[0]
                result = result[output_key]
                logger.debug(f"[GraphUtils] Unwrapped single output '{output_key}', new type: {type(result)}")
            elif "data" in result:
                # Prefer "data" output if multiple outputs exist
                result = result["data"]
                logger.debug(f"[GraphUtils] Unwrapped 'data' output from multi-output dict, new type: {type(result)}")
            else:
                # Multiple outputs and no "data" key - take first value
                output_key = list(result.keys())[0]
                result = result[output_key]
                logger.debug(
                    f"[GraphUtils] Unwrapped first output '{output_key}' from multi-output dict, new type: {type(result)}"
                )

        # Extract data from result
        # Check if result is already a list of Data objects
        if isinstance(result, list):
            # Direct list output (most common case for components)
            data_list = result
            logger.debug(f"[GraphUtils] Result is a list with {len(data_list)} items")
        elif isinstance(result, Data):
            # Single Data object
            data_list = [result]
            logger.debug("[GraphUtils] Result is a single Data object")
        elif hasattr(result, "data"):
            # Output object with .data attribute (e.g., Message with .data)
            data_list = result.data if isinstance(result.data, list) else [result.data]
            logger.debug("[GraphUtils] Extracted data from result.data attribute")
        else:
            # Single non-Data result
            data_list = [result]
            logger.debug("[GraphUtils] Wrapped single result in list")

        logger.debug(f"[GraphUtils] Extracted {len(data_list)} data records from vertex execution")

        # Convert to Data objects if needed
        result_data = []
        for i, item in enumerate(data_list):
            if isinstance(item, Data):
                result_data.append(item)
                logger.debug(
                    f"[GraphUtils] Item {i} is Data, keys: {list(item.data.keys()) if isinstance(item.data, dict) else 'NOT A DICT'}"
                )
            elif isinstance(item, dict):
                result_data.append(Data(data=item))
                logger.debug(f"[GraphUtils] Item {i} is dict, keys: {list(item.keys())}")
            else:
                logger.warning(f"[GraphUtils] Item {i} unexpected type: {type(item)}, wrapping as dict")
                result_data.append(Data(data={"value": item}))

        # Apply sample size limit if specified
        if sample_size is not None and len(result_data) > sample_size:
            result_data = result_data[:sample_size]
            logger.debug(f"[GraphUtils] Limited to {sample_size} records")

        logger.debug(f"[GraphUtils] Returning {len(result_data)} data records")
        return result_data

    except Exception:
        # Broad exception needed to handle various vertex execution failures
        logger.exception(f"[GraphUtils] Failed to execute node {node_id}")
        raise


def extract_fields_from_data(data_list: list[Data]) -> list[dict[str, Any]]:
    """Extract field information from Data objects.

    Args:
        data_list: List of Data objects

    Returns:
        List of field info dictionaries with field_name and sample_value
    """
    if not data_list:
        logger.warning("[GraphUtils] Empty data list provided")
        return []

    try:
        # Get the first record to extract field names
        first_record = data_list[0]
        if hasattr(first_record, "data"):
            data_dict = first_record.data
        elif isinstance(first_record, dict):
            data_dict = first_record
        else:
            logger.warning(f"[GraphUtils] Unexpected data type: {type(first_record)}")
            return []

        if not isinstance(data_dict, dict):
            logger.warning(f"[GraphUtils] Expected dict, got {type(data_dict)}")
            return []

        # Extract field names and create field info
        fields = [
            {
                "field_name": field_name,
                "sample_value": data_dict.get(field_name),
            }
            for field_name in data_dict
        ]

        logger.debug(f"[GraphUtils] Extracted {len(fields)} fields from data")
        return fields

    except Exception:  # noqa: BLE001
        # Broad exception needed to handle various data format issues
        logger.exception("[GraphUtils] Failed to extract fields")
        return []
