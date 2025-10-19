"""Utility functions for graph operations during component build configuration."""

from typing import TYPE_CHECKING, Any

from lfx.log.logger import logger
from lfx.schema import Data

if TYPE_CHECKING:
    from lfx.graph.graph.base import Graph


def find_upstream_node_id(graph_data: dict, target_node_id: str, input_name: str) -> str | None:
    """Find the upstream node ID connected to a specific input.

    Args:
        graph_data: Flow graph data containing nodes and edges
        target_node_id: ID of the target node
        input_name: Name of the input field to find upstream connection for

    Returns:
        ID of the upstream node, or None if not found
    """
    edges = graph_data.get("edges", [])

    for edge in edges:
        # Edge format: {source: "node1", target: "node2", targetHandle: "input_name"}
        if edge.get("target") == target_node_id and edge.get("targetHandle") == input_name:
            source_node_id = edge.get("source")
            logger.debug(
                f"[GraphUtils] Found upstream node '{source_node_id}' "
                f"connected to '{target_node_id}' input '{input_name}'"
            )
            return source_node_id

    logger.debug(f"[GraphUtils] No upstream node found for '{target_node_id}' input '{input_name}'")
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

        # Get the vertex for this node
        vertex = graph.get_vertex(node_id)
        if not vertex:
            msg = f"Node {node_id} not found in graph"
            raise ValueError(msg)

        logger.debug(f"[GraphUtils] Executing vertex '{node_id}' of type '{vertex.vertex_type}'")

        # Execute the vertex (this runs all dependencies automatically)
        result = await vertex.build()

        logger.debug(f"[GraphUtils] Vertex execution completed, result type: {type(result)}")

        # Extract data from result
        if hasattr(result, "data"):
            # Output object with .data attribute
            data_list = result.data if isinstance(result.data, list) else [result.data]
        elif isinstance(result, list):
            # Direct list output
            data_list = result
        else:
            # Single result
            data_list = [result]

        logger.debug(f"[GraphUtils] Extracted {len(data_list)} data records from vertex execution")

        # Convert to Data objects if needed
        result_data = []
        for item in data_list:
            if isinstance(item, Data):
                result_data.append(item)
            elif isinstance(item, dict):
                result_data.append(Data(data=item))
            else:
                logger.warning(f"[GraphUtils] Unexpected data type: {type(item)}, wrapping as dict")
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
