"""Lineage analysis service for ETL flows."""

from __future__ import annotations

import re
from typing import Any

import sqlparse
from lfx.log.logger import logger


class LineageAnalyzer:
    """Analyzes data lineage in ETL flows."""

    # ETL component types that represent table inputs
    TABLE_INPUT_TYPES = {
        "ETLTableInput",
        "ETLCSVInput",
        "ETLExcelInput",
        "ETLKafkaInput",
        "ETLCDCInput",
        "ETLAPIInput",
        "ETLCustomInput",
    }

    # ETL component types that represent table outputs
    TABLE_OUTPUT_TYPES = {
        "ETLTableOutput",
        "ETLCSVOutput",
        "ETLExcelOutput",
        "ETLKafkaOutput",
        "ETLAPIOutput",
    }

    # ETL transformation components
    TRANSFORMATION_TYPES = {
        "ETLFieldNameMapping",
        "ETLFieldValueMapping",
        "ETLFieldTypeConversion",
        "ETLDataCleaning",
        "ETLFieldSplit",
        "ETLFieldPivot",
        "ETLFieldUnpivot",
        "ETLFieldSplitToColumns",
        "ETLFieldValueMerge",
    }

    # ETL operation components
    OPERATION_TYPES = {
        "ETLDualStreamJoin",
        "ETLGroupBy",
        "ETLDeduplication",
        "ETLMultiStreamUnion",
    }

    def __init__(self, flow_data: dict[str, Any]):
        """Initialize the lineage analyzer.

        Args:
            flow_data: Flow data containing nodes and edges
        """
        self.flow_data = flow_data
        self.nodes = flow_data.get("nodes", [])
        self.edges = flow_data.get("edges", [])
        self.edge_index = self._build_edge_index()

    def _build_edge_index(self) -> dict[str, list[dict[str, Any]]]:
        """Build an index of edges for fast lookup.

        Returns:
            Dictionary mapping node_id to list of incoming edges
        """
        edge_index: dict[str, list[dict[str, Any]]] = {}

        for edge in self.edges:
            target_id = edge.get("target")
            if target_id:
                if target_id not in edge_index:
                    edge_index[target_id] = []
                edge_index[target_id].append(edge)

        return edge_index

    def _get_node_by_id(self, node_id: str) -> dict[str, Any] | None:
        """Get node by ID.

        Args:
            node_id: Node ID to find

        Returns:
            Node data or None if not found
        """
        for node in self.nodes:
            if node.get("id") == node_id:
                return node
        return None

    def _get_node_type(self, node: dict[str, Any]) -> str:
        """Get the type of a node.

        Args:
            node: Node data

        Returns:
            Node type string
        """
        return node.get("data", {}).get("type", "")

    def _get_node_template(self, node: dict[str, Any]) -> dict[str, Any]:
        """Get the template/configuration of a node.

        Args:
            node: Node data

        Returns:
            Template dictionary
        """
        return node.get("data", {}).get("node", {}).get("template", {})

    def _get_template_value(self, template: dict[str, Any], key: str) -> Any:
        """Get a value from template.

        Args:
            template: Template dictionary
            key: Key to retrieve

        Returns:
            Value or None if not found
        """
        field = template.get(key, {})
        if isinstance(field, dict):
            return field.get("value")
        return field

    def _extract_table_name_from_sql(self, sql: str) -> str | None:
        """Extract table name from SQL query.

        Args:
            sql: SQL query string

        Returns:
            Table name or None
        """
        if not sql:
            return None

        try:
            # Parse SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                return None

            # Get the first statement
            stmt = parsed[0]

            # Try to extract table name from FROM clause
            from_seen = False
            for token in stmt.tokens:
                if from_seen:
                    if token.ttype is None and isinstance(token, sqlparse.sql.Identifier):
                        return str(token.get_real_name())
                    if token.ttype is not None and token.ttype not in (
                        sqlparse.tokens.Whitespace,
                        sqlparse.tokens.Newline,
                    ):
                        return str(token.value)
                if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                    from_seen = True

            # Fallback: simple regex for common patterns
            match = re.search(r"FROM\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)
            if match:
                return match.group(1)

        except Exception:
            pass

        return None

    def _extract_table_info(self, node: dict[str, Any]) -> dict[str, Any] | None:
        """Extract table information from a table input/output node.

        Args:
            node: Node data

        Returns:
            Table information dictionary or None
        """
        node_type = self._get_node_type(node)
        node_id = node.get("id", "")
        template = self._get_node_template(node)

        # Determine if this is a source or target table
        is_source = node_type in self.TABLE_INPUT_TYPES
        is_target = node_type in self.TABLE_OUTPUT_TYPES

        if not (is_source or is_target):
            return None

        # Extract basic info
        table_info: dict[str, Any] = {
            "id": f"table-{node_id}",
            "node_id": node_id,
            "node_type": node_type,
            "node_name": node.get("data", {}).get("node", {}).get("display_name", node_type),
            "type": "source" if is_source else "target",
        }

        # Extract datasource information
        datasource_selector = self._get_template_value(template, "datasource_selector")
        if datasource_selector:
            table_info["datasource_id"] = datasource_selector
            # Try to get datasource name from options
            datasource_field = template.get("datasource_selector", {})
            if isinstance(datasource_field, dict):
                options = datasource_field.get("options", [])
                for option in options:
                    if isinstance(option, dict) and option.get("value") == datasource_selector:
                        table_info["datasource_name"] = option.get("label", "Unknown")
                        break

        # Extract table name
        table_name = None

        # Method 1: Direct table selector
        table_selector = self._get_template_value(template, "table_selector")
        if table_selector:
            table_name = table_selector

        # Method 2: From SQL query
        if not table_name:
            sql_query = self._get_template_value(template, "sql_query")
            if sql_query:
                table_name = self._extract_table_name_from_sql(sql_query)

        # Method 3: From file path (for CSV/Excel)
        if not table_name and node_type in {"ETLCSVInput", "ETLCSVOutput", "ETLExcelInput", "ETLExcelOutput"}:
            file_path = self._get_template_value(template, "file_path")
            if file_path:
                # Extract filename without extension
                import os

                table_name = os.path.splitext(os.path.basename(file_path))[0]

        # Method 4: From topic name (for Kafka)
        if not table_name and node_type in {"ETLKafkaInput", "ETLKafkaOutput"}:
            topic = self._get_template_value(template, "topic")
            if topic:
                table_name = topic

        table_info["table_name"] = table_name or "Unknown"

        # Extract field mappings
        field_mappings = self._get_template_value(template, "field_mappings")
        if field_mappings and isinstance(field_mappings, list):
            fields = []
            for mapping in field_mappings:
                if isinstance(mapping, dict):
                    # For input nodes
                    if is_source:
                        field_name = mapping.get("source_field") or mapping.get("field_name")
                        if field_name:
                            fields.append(
                                {
                                    "name": field_name,
                                    "type": mapping.get("data_type", "string"),
                                    "is_key": mapping.get("is_key_field", False),
                                }
                            )
                    # For output nodes
                    else:
                        source_field = mapping.get("source_field")
                        target_field = mapping.get("target_field", source_field)
                        if target_field:
                            field_info = {
                                "name": target_field,
                                "type": mapping.get("data_type", "string"),
                                "is_key": mapping.get("is_key_field", False),
                            }
                            if source_field and source_field != target_field:
                                field_info["source_field"] = source_field
                            fields.append(field_info)

            if fields:
                table_info["fields"] = fields

        return table_info

    def _find_upstream_nodes(self, node_id: str, visited: set[str] | None = None) -> list[str]:
        """Find all upstream nodes (BFS).

        Args:
            node_id: Starting node ID
            visited: Set of already visited nodes

        Returns:
            List of upstream node IDs
        """
        if visited is None:
            visited = set()

        upstream_nodes = []
        edges = self.edge_index.get(node_id, [])

        for edge in edges:
            source_id = edge.get("source")
            if source_id and source_id not in visited:
                visited.add(source_id)
                upstream_nodes.append(source_id)
                # Recursively find upstream
                upstream_nodes.extend(self._find_upstream_nodes(source_id, visited))

        return upstream_nodes

    def _trace_path_to_source(self, target_node_id: str) -> list[list[str]]:
        """Trace all paths from target node back to source tables.

        Args:
            target_node_id: Target node ID

        Returns:
            List of paths (each path is a list of node IDs)
        """
        paths: list[list[str]] = []

        def dfs(current_id: str, path: list[str], visited: set[str]) -> None:
            # Check if this is a source table
            node = self._get_node_by_id(current_id)
            if node and self._get_node_type(node) in self.TABLE_INPUT_TYPES:
                paths.append(path[::-1])  # Reverse to get source->target order
                return

            # Get upstream edges
            edges = self.edge_index.get(current_id, [])
            if not edges:
                # Dead end (no upstream)
                return

            for edge in edges:
                source_id = edge.get("source")
                if source_id and source_id not in visited:
                    visited.add(source_id)
                    path.append(source_id)
                    dfs(source_id, path, visited)
                    path.pop()
                    visited.remove(source_id)

        # Start DFS from target
        visited_nodes: set[str] = {target_node_id}
        dfs(target_node_id, [target_node_id], visited_nodes)

        return paths

    def _analyze_field_transformations(self, path: list[str]) -> list[dict[str, Any]]:
        """Analyze field transformations along a path.

        Args:
            path: List of node IDs representing a data flow path

        Returns:
            List of field mapping dictionaries
        """
        field_mappings = []

        # Get source table fields
        source_node = self._get_node_by_id(path[0])
        if not source_node:
            logger.debug(f"DEBUG: Source node not found for path[0]: {path[0]}")
            return field_mappings

        source_table_info = self._extract_table_info(source_node)
        if not source_table_info or "fields" not in source_table_info:
            logger.debug(f"DEBUG: No source table info or fields for node: {path[0]}")
            return field_mappings

        logger.debug(f"DEBUG: Source table has {len(source_table_info['fields'])} fields")

        # Track field transformations through the path
        current_fields = {f["name"]: f for f in source_table_info["fields"]}
        logger.debug(f"DEBUG: Initial current_fields: {list(current_fields.keys())}")

        for i in range(1, len(path)):
            node = self._get_node_by_id(path[i])
            if not node:
                logger.debug(f"DEBUG: Node not found at path[{i}]: {path[i]}")
                continue

            node_type = self._get_node_type(node)
            logger.debug(f"DEBUG: Processing node type: {node_type} at path[{i}]")
            logger.debug(f"DEBUG: Current fields before processing: {list(current_fields.keys())}")
            template = self._get_node_template(node)

            # Handle field name mapping
            if node_type == "ETLFieldNameMapping":
                mappings = self._get_template_value(template, "field_mappings")
                if mappings and isinstance(mappings, list):
                    new_fields = {}
                    for mapping in mappings:
                        if isinstance(mapping, dict):
                            source_field = mapping.get("source_field")
                            target_field = mapping.get("target_field", source_field)
                            if source_field in current_fields:
                                field_info = current_fields[source_field].copy()
                                field_info["name"] = target_field
                                if source_field != target_field:
                                    if "transformations" not in field_info:
                                        field_info["transformations"] = []
                                    field_info["transformations"].append(
                                        {"type": "rename", "from": source_field, "to": target_field, "node": node["id"]}
                                    )
                                new_fields[target_field] = field_info

                    # Update current fields
                    drop_unmapped = self._get_template_value(template, "drop_unmapped")
                    if drop_unmapped:
                        current_fields = new_fields
                    else:
                        current_fields.update(new_fields)

            # Handle field type conversion
            elif node_type == "ETLFieldTypeConversion":
                conversions = self._get_template_value(template, "field_type_conversions")
                if conversions and isinstance(conversions, list):
                    for conversion in conversions:
                        if isinstance(conversion, dict):
                            field_name = conversion.get("field_name")
                            new_type = conversion.get("target_type")
                            if field_name in current_fields and new_type:
                                field_info = current_fields[field_name]
                                old_type = field_info.get("type")
                                field_info["type"] = new_type
                                if "transformations" not in field_info:
                                    field_info["transformations"] = []
                                field_info["transformations"].append(
                                    {
                                        "type": "type_conversion",
                                        "from": old_type,
                                        "to": new_type,
                                        "node": node["id"],
                                    }
                                )

            # Handle other transformation components (data cleaning, etc.)
            # These components pass through all fields without modification
            elif node_type in self.TRANSFORMATION_TYPES or node_type in self.OPERATION_TYPES:
                # For transformation/operation components that don't explicitly change field structure,
                # we pass through all current fields unchanged
                logger.debug(f"DEBUG: Passing through transformation component: {node_type}")

            # Handle output table field mapping
            elif node_type in self.TABLE_OUTPUT_TYPES:
                logger.debug(f"DEBUG: Processing output table: {node_type}")
                target_table_info = self._extract_table_info(node)
                if target_table_info and "fields" in target_table_info:
                    logger.debug(f"DEBUG: Target table has {len(target_table_info['fields'])} fields")
                    logger.debug(f"DEBUG: Current fields available: {list(current_fields.keys())}")
                    for target_field in target_table_info["fields"]:
                        source_field_name = target_field.get("source_field", target_field["name"])
                        logger.debug(
                            f"DEBUG: Trying to map target field '{target_field['name']}' from source field '{source_field_name}'"
                        )
                        if source_field_name in current_fields:
                            logger.debug(f"DEBUG: Found mapping: {source_field_name} -> {target_field['name']}")
                            source_field_info = current_fields[source_field_name]
                            transformations = source_field_info.get("transformations", [])

                            # Find the original source field name by tracing back transformations
                            original_source_field = source_field_name
                            if transformations:
                                for trans in transformations:
                                    if trans.get("type") == "rename" and trans.get("from"):
                                        original_source_field = trans["from"]
                                        break

                            field_mappings.append(
                                {
                                    "source_field": original_source_field,
                                    "target_field": target_field["name"],
                                    "source_type": source_field_info.get("type", "string"),
                                    "target_type": target_field.get("type", "string"),
                                    "transformations": [t["type"] for t in transformations] if transformations else [],
                                }
                            )
                        else:
                            logger.debug(f"DEBUG: Field '{source_field_name}' NOT found in current_fields!")
                else:
                    logger.debug("DEBUG: No target table info or fields found")

        logger.debug(f"DEBUG: Final field_mappings count: {len(field_mappings)}")
        return field_mappings

    def extract_table_nodes(self) -> list[dict[str, Any]]:
        """Extract all table input and output nodes.

        Returns:
            List of table information dictionaries
        """
        table_nodes = []

        for node in self.nodes:
            node_type = self._get_node_type(node)
            if node_type in self.TABLE_INPUT_TYPES or node_type in self.TABLE_OUTPUT_TYPES:
                table_info = self._extract_table_info(node)
                if table_info:
                    table_nodes.append(table_info)

        return table_nodes

    def build_lineage_relationships(self, table_nodes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """Build lineage relationships between tables.

        Args:
            table_nodes: Optional list of table nodes to analyze

        Returns:
            List of relationship dictionaries
        """
        if table_nodes is None:
            table_nodes = self.extract_table_nodes()

        relationships = []

        # Find all target tables (outputs)
        target_tables = [t for t in table_nodes if t["type"] == "target"]

        for target_table in target_tables:
            # Trace paths back to source tables
            paths = self._trace_path_to_source(target_table["node_id"])

            for path in paths:
                if len(path) < 2:
                    continue

                # Get source table
                source_node = self._get_node_by_id(path[0])
                if not source_node:
                    continue

                source_table_info = self._extract_table_info(source_node)
                if not source_table_info:
                    continue

                # Get transformation nodes (exclude source and target)
                transformation_nodes = []
                for node_id in path[1:-1]:
                    node = self._get_node_by_id(node_id)
                    if node:
                        node_type = self._get_node_type(node)
                        if (
                            node_type in self.TRANSFORMATION_TYPES
                            or node_type in self.OPERATION_TYPES
                            or "ETL" in node_type
                        ):
                            transformation_nodes.append(
                                {
                                    "id": node_id,
                                    "type": node_type,
                                    "name": node.get("data", {}).get("node", {}).get("display_name", node_type),
                                }
                            )

                # Analyze field transformations
                field_mappings = self._analyze_field_transformations(path)

                relationship_data = {
                    "id": f"rel-{source_table_info['id']}-{target_table['id']}",
                    "source_table_id": source_table_info["id"],
                    "source_table_name": source_table_info["table_name"],
                    "target_table_id": target_table["id"],
                    "target_table_name": target_table["table_name"],
                    "transformation_path": transformation_nodes,
                    "field_mappings": field_mappings,
                }

                logger.debug(f"DEBUG: Created relationship with {len(transformation_nodes)} transformation nodes")
                logger.debug(f"DEBUG: Transformation nodes: {[n['name'] for n in transformation_nodes]}")
                logger.debug(f"DEBUG: Relationship data: {relationship_data}")

                relationships.append(relationship_data)

        return relationships

    def analyze(self, table_name: str | None = None, exact_match: bool = False) -> dict[str, Any]:
        """Analyze the flow and generate lineage information.

        Args:
            table_name: Optional table name to filter results
            exact_match: If True, use exact match; if False, use fuzzy match (default)

        Returns:
            Dictionary containing tables and relationships
        """
        # Extract all table nodes
        all_tables = self.extract_table_nodes()

        # Filter by table name if specified
        if table_name:
            filtered_tables = []
            for table in all_tables:
                table_name_value = table.get("table_name", "")
                if exact_match:
                    # Exact match: case-insensitive equality
                    if table_name.lower() == table_name_value.lower():
                        filtered_tables.append(table)
                # Fuzzy match: case-insensitive substring match
                elif table_name.lower() in table_name_value.lower():
                    filtered_tables.append(table)
            tables_to_analyze = filtered_tables
        else:
            tables_to_analyze = all_tables

        # Build relationships
        relationships = self.build_lineage_relationships(all_tables)

        # Filter relationships if table name specified
        if table_name and tables_to_analyze:
            table_ids = {t["id"] for t in tables_to_analyze}
            filtered_relationships = []
            for rel in relationships:
                if rel["source_table_id"] in table_ids or rel["target_table_id"] in table_ids:
                    filtered_relationships.append(rel)
            relationships = filtered_relationships

        return {
            "tables": tables_to_analyze if table_name else all_tables,
            "relationships": relationships,
            "total_tables": len(all_tables),
            "total_relationships": len(relationships),
        }
