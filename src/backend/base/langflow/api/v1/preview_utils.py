"""Utility functions for previewing upstream node data."""

import pandas as pd
from lfx.graph.graph.base import Graph
from lfx.log.logger import logger
from lfx.schema import Data

from langflow.api.v1.schemas import FieldSchema


def find_upstream_node(flow_data: dict, target_node_id: str, input_name: str) -> str | None:
    """Find the upstream node connected to a specific input of the target node.

    Args:
        flow_data: Complete flow graph data with nodes and edges
        target_node_id: ID of the node whose upstream we want to find
        input_name: Name of the input field (e.g., "data_input")

    Returns:
        ID of the upstream node, or None if not found
    """
    edges = flow_data.get("edges", [])

    # Find edge connecting to our input
    # Edge format: { source: "node1", sourceHandle: "output_name", target: "node2", targetHandle: "input_name" }
    for edge in edges:
        if edge.get("target") == target_node_id and edge.get("targetHandle") == input_name:
            source_node_id = edge.get("source")
            logger.info(
                f"[PreviewUtils] Found upstream node '{source_node_id}' connected to '{target_node_id}' input '{input_name}'"
            )
            return source_node_id

    logger.warning(f"[PreviewUtils] No upstream node found for '{target_node_id}' input '{input_name}'")
    return None


async def execute_upstream_node(flow_data: dict, node_id: str, sample_size: int = 10) -> list[Data]:
    """Execute a specific upstream node and return sample data.

    Args:
        flow_data: Complete flow graph data
        node_id: ID of the node to execute
        sample_size: Number of records to sample

    Returns:
        List of Data objects from node execution

    Raises:
        ValueError: If node not found or execution fails
    """
    try:
        logger.info(f"[PreviewUtils] Building graph to execute node '{node_id}'")

        # 1. Build graph from flow data
        graph = Graph.from_payload(flow_data)

        # 2. Find target vertex
        vertex = graph.get_vertex(node_id)
        if not vertex:
            msg = f"Node {node_id} not found in graph"
            raise ValueError(msg)

        logger.info(f"[PreviewUtils] Executing vertex '{node_id}' of type '{vertex.vertex_type}'")

        # 3. Execute vertex (runs all dependencies automatically)
        result = await vertex.build()

        logger.debug(f"[PreviewUtils] Vertex execution completed, result type: {type(result)}")

        # 4. Extract data output
        # Most components output Data objects or list[Data]
        data_list = []

        if hasattr(result, "data"):
            # Single output: Output class with .data attribute
            if isinstance(result.data, list):
                data_list = result.data
            else:
                data_list = [result.data]
        elif isinstance(result, list):
            # Direct list output
            data_list = result
        else:
            # Wrap single result
            data_list = [result]

        logger.info(f"[PreviewUtils] Extracted {len(data_list)} data records from vertex execution")

        # 5. Sample data (first N records)
        sampled = data_list[:sample_size]

        # 6. Convert to Data objects if needed
        result_data = []
        for item in sampled:
            if isinstance(item, Data):
                result_data.append(item)
            elif isinstance(item, dict):
                result_data.append(Data(data=item))
            else:
                logger.warning(f"[PreviewUtils] Unexpected data type: {type(item)}, wrapping as dict")
                result_data.append(Data(data={"value": item}))

        logger.info(f"[PreviewUtils] Successfully sampled {len(result_data)} records")
        return result_data

    except Exception as e:
        logger.error(f"[PreviewUtils] Failed to execute upstream node {node_id}: {e}", exc_info=True)
        raise


def analyze_field_structure(data_list: list[Data]) -> list[FieldSchema]:
    """Analyze field structure from Data objects.

    Args:
        data_list: List of Data objects

    Returns:
        List of FieldSchema with field names, types, and sample values
    """
    if not data_list:
        logger.warning("[PreviewUtils] Empty data list provided for field analysis")
        return []

    try:
        # Convert to DataFrame for type inference
        records = []
        for d in data_list:
            if hasattr(d, "data"):
                records.append(d.data)
            elif isinstance(d, dict):
                records.append(d)
            else:
                logger.warning(f"[PreviewUtils] Unexpected data type in list: {type(d)}")

        if not records:
            logger.warning("[PreviewUtils] No valid records found in data list")
            return []

        df = pd.DataFrame(records)

        logger.info(f"[PreviewUtils] Analyzing {len(df.columns)} fields from {len(df)} records")

        fields = []
        for col in df.columns:
            # Infer data type from pandas dtype
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                data_type = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                data_type = "float"
            elif pd.api.types.is_bool_dtype(dtype):
                data_type = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                data_type = "datetime"
            else:
                data_type = "string"

            # Get sample values (first 3 non-null values, converted to strings for JSON)
            sample_values_series = df[col].dropna().head(3)
            sample_values = sample_values_series.tolist() if len(sample_values_series) > 0 else None

            field = FieldSchema(field_name=col, data_type=data_type, sample_values=sample_values)
            fields.append(field)

            logger.debug(f"[PreviewUtils] Field '{col}': type={data_type}, samples={sample_values}")

        logger.info(f"[PreviewUtils] Successfully analyzed {len(fields)} fields")
        return fields

    except Exception as e:
        logger.error(f"[PreviewUtils] Field analysis failed: {e}", exc_info=True)
        raise
