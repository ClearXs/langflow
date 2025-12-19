"""Custom Input Component for ETL operations."""

from datetime import datetime
from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


def _format_i18n(key: str, **kwargs) -> str:
    """Helper function to format i18n strings with parameters.

    The i18n library's parameter substitution doesn't work properly,
    so we manually replace {param} placeholders.
    """
    text = i18n.t(key)
    for param_key, param_value in kwargs.items():
        text = text.replace(f"{{{param_key}}}", str(param_value))
    return text


class ETLCustomInputComponent(Component):
    """Custom data input component with user-defined schema for testing."""

    display_name = i18n.t("components.input_output.custom_input.display_name")
    description = i18n.t("components.input_output.custom_input.description")
    icon = "TestTube2"
    name = "ETLCustomInput"

    inputs = [
        HandleInput(
            name="upstream_data",
            display_name=i18n.t("components.input_output.custom_input.upstream_data.display_name"),
            info=i18n.t("components.input_output.custom_input.upstream_data.info"),
            input_types=["Data"],
            is_list=True,
            required=False,
            advanced=False,
        ),
        TableInput(
            name="field_schema",
            display_name=i18n.t("components.input_output.custom_input.field_schema.display_name"),
            info=i18n.t("components.input_output.custom_input.field_schema.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.field_name"),
                    "type": "str",
                    "required": True,
                },
                {
                    "name": "data_type",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.data_type"),
                    "type": "str",
                    "formatter": "text",
                    "options": [
                        "string",
                        "integer",
                        "float",
                        "boolean",
                        "datetime",
                        "json",
                        "point",
                        "linestring",
                        "polygon",
                        "multipoint",
                        "multilinestring",
                        "multipolygon",
                        "geometry",
                        "geography",
                    ],
                },
                {
                    "name": "value_source",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.value_source"),
                    "type": "str",
                    "formatter": "text",
                    "options": [
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.from_upstream"),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.generate_id"),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.use_variable"),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.current_time"),
                        i18n.t(
                            "components.input_output.custom_input.field_schema.value_source_options.current_timestamp"
                        ),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.sequence"),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.fixed_value"),
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.expression"),
                    ],
                    "default": i18n.t(
                        "components.input_output.custom_input.field_schema.value_source_options.use_variable"
                    ),
                },
                {
                    "name": "default_value",
                    "display_name": i18n.t("components.input_output.custom_input.field_schema.default_value"),
                    "type": "str",
                    "formatter": "text",  # Required for dropdown editor
                    "depend_on": "value_source",
                    "options_map": {
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.generate_id"): [
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.uuid"),
                                "value": "UUID",
                            },
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.snowflake"),
                                "value": "雪花ID",
                            },
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.auto_increment"),
                                "value": "自增ID",
                            },
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.ulid"),
                                "value": "ULID",
                            },
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.nanoid"),
                                "value": "NanoID",
                            },
                            {
                                "label": i18n.t("components.input_output.custom_input.id_types.timestamp"),
                                "value": "时间戳ID",
                            },
                        ],
                        i18n.t("components.input_output.custom_input.field_schema.value_source_options.current_time"): [
                            {"label": "yyyy-MM-dd HH:mm:ss", "value": "%Y-%m-%d %H:%M:%S"},
                            {"label": "yyyy-MM-dd", "value": "%Y-%m-%d"},
                            {"label": "yyyy年MM月dd日 HH:mm:ss", "value": "%Y年%m月%d日 %H:%M:%S"},
                            {"label": "yyyy年MM月dd日", "value": "%Y年%m月%d日"},
                            {"label": "yyyyMMddHHmmss", "value": "%Y%m%d%H%M%S"},
                            {"label": "yyyy-MM-ddTHH:mm:ss+08:00", "value": "%Y-%m-%dT%H:%M:%S+08:00"},
                            {"label": "yyyy/MM/dd HH:mm:ss", "value": "%Y/%m/%d %H:%M:%S"},
                            {"label": "dd/MM/yyyy HH:mm:ss", "value": "%d/%m/%Y %H:%M:%S"},
                            {"label": "MM/dd/yyyy hh:mm:ss a", "value": "%m/%d/%Y %I:%M:%S %p"},
                        ],
                        i18n.t(
                            "components.input_output.custom_input.field_schema.value_source_options.current_timestamp"
                        ): [
                            {
                                "label": i18n.t("components.input_output.custom_input.timestamp_types.seconds"),
                                "value": "秒",
                            },
                        ],
                    },
                },
            ],
            value=[],
            table_options={
                "block_add": False,  # Allow adding fields
                "block_delete": False,  # Allow deleting fields
                "block_edit": False,  # Allow editing
                # Removed apply_schema button - auto-sync on field_schema change
            },
            advanced=False,
        ),
        TableInput(
            name="preview_table",
            display_name=i18n.t("components.input_output.custom_input.preview_table.display_name"),
            info=i18n.t("components.input_output.custom_input.preview_table.info"),
            table_schema=[],  # Will be dynamically generated from field_schema
            value=[],
            table_options={
                "block_add": True,  # Disable adding rows
                "block_delete": True,  # Disable deleting rows
                "block_edit": True,  # Disable editing
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "preview_data",
                        "label": i18n.t("components.input_output.custom_input.preview_table.preview_button"),
                        "icon": "Eye",
                        "position": "top",
                    },
                ],
            },
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.custom_input.output_data.display_name"),
            method="load_data",
        ),
    ]

    def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Handle dynamic configuration updates and action buttons."""
        logger.info(
            f"[CustomInput] update_build_config called - field_name: {field_name}, "
            f"field_value type: {type(field_value).__name__ if field_value is not None else 'None'}, "
            f"action: {action}"
        )

        # Debug: Log field_schema configuration to verify options_map and depend_on
        if field_name == "field_schema" or action == "load":
            field_schema_config = build_config.get("field_schema", {})
            table_schema = field_schema_config.get("table_schema", [])
            logger.info(f"[CustomInput] field_schema table_schema has {len(table_schema)} columns")
            for col in table_schema:
                if col.get("name") == "default_value":
                    logger.info(
                        f"[CustomInput] default_value column config: "
                        f"depend_on={col.get('depend_on')}, "
                        f"has_options_map={bool(col.get('options_map'))}, "
                        f"options_map_keys={list(col.get('options_map', {}).keys())}"
                    )

        # ALWAYS sync preview_table schema on ANY update_build_config call
        try:
            field_schema = build_config.get("field_schema", {}).get("value", [])
            current_preview_schema = build_config.get("preview_table", {}).get("table_schema", [])

            # Only update if we have a field_schema
            if field_schema:
                # Generate expected schema
                expected_schema = self._generate_schema_from_fields(field_schema)

                # Check if preview_table schema needs update
                preview_schema_changed = len(current_preview_schema) != len(expected_schema)
                if not preview_schema_changed and len(expected_schema) > 0:
                    current_preview_names = {f.get("name") for f in current_preview_schema}
                    expected_names = {f.get("name") for f in expected_schema}
                    preview_schema_changed = current_preview_names != expected_names

                if preview_schema_changed:
                    logger.info(f"[CustomInput] Syncing preview_table schema with {len(expected_schema)} fields")
                    build_config["preview_table"]["table_schema"] = expected_schema

        except Exception as e:  # noqa: BLE001
            logger.error(f"[CustomInput] Error during auto-sync: {e}")

        # Handle "Preview Data" action
        if field_name == "preview_table" and action == "preview_data":
            logger.info("[CustomInput] Preview data action triggered")
            try:
                import asyncio

                # Get current field schema
                field_schema = build_config.get("field_schema", {}).get("value", [])

                if not field_schema:
                    self.status = i18n.t("components.input_output.custom_input.errors.no_schema")
                    logger.warning("[CustomInput] No field schema defined for preview")
                    return build_config

                # Ensure preview_table schema is synced
                preview_schema = self._generate_schema_from_fields(field_schema)
                build_config["preview_table"]["table_schema"] = preview_schema

                # Generate preview data (10 sample rows)
                # Need to run async method in sync context, passing build_config for upstream data access
                preview_data = asyncio.run(self._generate_preview_data(field_schema, build_config, sample_size=10))

                # Update preview_table with generated data
                build_config["preview_table"]["value"] = preview_data

                self.status = _format_i18n(
                    "components.input_output.custom_input.status.preview_generated", count=len(preview_data)
                )
                logger.info(f"[CustomInput] Generated {len(preview_data)} preview records")

            except Exception as e:  # noqa: BLE001 - Catch all for config updates
                error_msg = str(e)
                self.status = _format_i18n(
                    "components.input_output.custom_input.errors.preview_failed", error=error_msg
                )
                logger.exception(f"[CustomInput] Preview data generation failed: {error_msg}")

        return build_config

    def _generate_schema_from_fields(self, field_schema: list[dict]) -> list[dict]:
        """Convert field schema rows to TableInput table_schema format.

        Args:
            field_schema: List of field definitions with field_name, data_type, default_value

        Returns:
            List of table schema definitions for TableInput
        """
        table_schema = []

        for field in field_schema:
            field_name = field.get("field_name")
            data_type = field.get("data_type", "string")

            if not field_name:
                continue

            # Map data types to frontend types
            frontend_type = "str"  # Default
            if data_type == "integer":
                frontend_type = "int"
            elif data_type == "float":
                frontend_type = "float"
            elif data_type == "boolean":
                frontend_type = "bool"
            elif data_type == "datetime":
                frontend_type = "str"  # DateTime rendered as string in table
            elif data_type == "json":
                frontend_type = "str"  # JSON rendered as string in table
            elif data_type in (
                "point",
                "linestring",
                "polygon",
                "multipoint",
                "multilinestring",
                "multipolygon",
                "geometry",
                "geography",
            ):
                frontend_type = "str"  # Spatial types rendered as string (JSON) in table

            table_schema.append(
                {
                    "name": field_name,
                    "display_name": field_name,
                    "type": frontend_type,
                    "disable_edit": False,  # Allow editing
                }
            )

        return table_schema

    def _convert_value(self, value: Any, data_type: str) -> Any:
        """Convert value to target data type.

        Args:
            value: Input value (typically string from UI)
            data_type: Target data type

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        if value is None or value == "":
            return None

        try:
            if data_type == "string":
                return str(value)

            if data_type == "integer":
                return int(value)

            if data_type == "float":
                return float(value)

            if data_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    value_lower = value.lower().strip()
                    if value_lower in ("true", "1", "yes", "y", "on"):
                        return True
                    if value_lower in ("false", "0", "no", "n", "off"):
                        return False
                    raise ValueError(f"Cannot convert '{value}' to boolean")
                return bool(value)

            if data_type == "datetime":
                if isinstance(value, datetime):
                    return value.isoformat()
                # Try to parse datetime string
                try:
                    dt = pd.to_datetime(value)
                    return dt.isoformat()
                except Exception as e:
                    raise ValueError(f"Cannot parse datetime: {e}")

            # JSON type handling
            if data_type == "json":
                if isinstance(value, (dict, list)):
                    # Already a dict/list, return as-is
                    return value
                if isinstance(value, str):
                    # Try to parse JSON string
                    import json

                    try:
                        return json.loads(value)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON format: {e}")
                # If it's a Data object, extract its data attribute
                if hasattr(value, "data"):
                    return value.data
                raise ValueError(f"Cannot convert {type(value).__name__} to JSON")

            # Spatial types - validate GeoJSON format
            if data_type in (
                "point",
                "linestring",
                "polygon",
                "multipoint",
                "multilinestring",
                "multipolygon",
                "geometry",
                "geography",
            ):
                # If already a dict (GeoJSON object), validate and return
                if isinstance(value, dict):
                    if "type" not in value or "coordinates" not in value:
                        raise ValueError("Invalid GeoJSON format: missing 'type' or 'coordinates'")
                    return value

                # If string, try to parse as JSON
                if isinstance(value, str):
                    import json

                    try:
                        geojson = json.loads(value)
                        if not isinstance(geojson, dict):
                            raise ValueError("GeoJSON must be an object")
                        if "type" not in geojson or "coordinates" not in geojson:
                            raise ValueError("Invalid GeoJSON format: missing 'type' or 'coordinates'")
                        return geojson
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Cannot parse GeoJSON: {e}")

                raise ValueError(f"Cannot convert {type(value)} to GeoJSON")

            return str(value)

        except (ValueError, TypeError) as e:
            raise ValueError(
                _format_i18n(
                    "components.input_output.custom_input.errors.type_conversion_failed",
                    value=str(value),
                    type=data_type,
                )
            ) from e

    def _generate_id(self, id_type: str, index: int) -> str:
        """Generate ID based on specified type.

        Args:
            id_type: ID type (UUID/Snowflake ID/Auto-increment/ULID/NanoID/Timestamp ID)
            index: Current record index (for auto-increment)

        Returns:
            Generated ID string
        """
        import time
        import uuid

        # Normalize id_type to handle both English and Chinese
        id_type_normalized = id_type.strip()

        # UUID
        if id_type_normalized in ("UUID", i18n.t("components.input_output.custom_input.id_types.uuid")):
            return str(uuid.uuid4())

        # Snowflake ID (simplified implementation using timestamp + random)
        if id_type_normalized in (
            "Snowflake ID",
            "雪花ID",
            i18n.t("components.input_output.custom_input.id_types.snowflake"),
        ):
            # Simplified snowflake: timestamp (41 bits) + machine id (10 bits) + sequence (12 bits)
            timestamp_ms = int(time.time() * 1000)
            machine_id = 1  # Fixed machine ID for simplicity
            sequence = index % 4096  # Sequence number from index
            snowflake_id = (timestamp_ms << 22) | (machine_id << 12) | sequence
            return str(snowflake_id)

        # Auto-increment ID
        if id_type_normalized in (
            "Auto Increment ID",
            "自增ID",
            i18n.t("components.input_output.custom_input.id_types.auto_increment"),
        ):
            return str(index + 1)

        # ULID
        if id_type_normalized in ("ULID", i18n.t("components.input_output.custom_input.id_types.ulid")):
            try:
                import ulid

                return str(ulid.new())
            except ImportError:
                logger.warning("[CustomInput] ulid library not available, using UUID as fallback")
                return str(uuid.uuid4())

        # NanoID
        if id_type_normalized in ("NanoID", i18n.t("components.input_output.custom_input.id_types.nanoid")):
            try:
                from nanoid import generate

                return generate()
            except ImportError:
                logger.warning("[CustomInput] nanoid library not available, using UUID as fallback")
                return str(uuid.uuid4())

        # Timestamp ID
        if id_type_normalized in (
            "Timestamp ID",
            "时间戳ID",
            i18n.t("components.input_output.custom_input.id_types.timestamp"),
        ):
            # Generate timestamp ID (milliseconds)
            return str(int(time.time() * 1000))

        # Unknown type - default to UUID
        logger.warning(f"[CustomInput] Unknown ID type: {id_type}, using UUID as fallback")
        return str(uuid.uuid4())

    def _generate_current_time(self, format_str: str) -> str:
        """Generate current time in China timezone (Asia/Shanghai).

        Args:
            format_str: Python strftime format string

        Returns:
            Formatted time string
        """
        from datetime import datetime

        try:
            # Try Python 3.9+ zoneinfo first
            from zoneinfo import ZoneInfo

            china_tz = ZoneInfo("Asia/Shanghai")
        except ImportError:
            # Fallback to pytz for Python 3.8
            try:
                import pytz

                china_tz = pytz.timezone("Asia/Shanghai")
            except ImportError:
                # If no timezone library available, use UTC+8 offset
                from datetime import timedelta, timezone

                china_tz = timezone(timedelta(hours=8))

        now = datetime.now(china_tz)
        return now.strftime(format_str)

    def _generate_current_timestamp(self, precision: str = "秒") -> str:
        """Generate current timestamp in China timezone (Asia/Shanghai).

        Args:
            precision: Timestamp precision ("秒" for seconds)

        Returns:
            Timestamp string
        """
        from datetime import datetime

        try:
            # Try Python 3.9+ zoneinfo first
            from zoneinfo import ZoneInfo

            china_tz = ZoneInfo("Asia/Shanghai")
        except ImportError:
            # Fallback to pytz for Python 3.8
            try:
                import pytz

                china_tz = pytz.timezone("Asia/Shanghai")
            except ImportError:
                # If no timezone library available, use UTC+8 offset
                from datetime import timedelta, timezone

                china_tz = timezone(timedelta(hours=8))

        now = datetime.now(china_tz)

        # Only seconds supported
        return str(int(now.timestamp()))

    def _generate_sequence(self, config: str, index: int) -> str:
        """Generate sequence number.

        Args:
            config: Sequence configuration "起始值:步长" (e.g., "1:1", "100:10")
            index: Current row index (from 0)

        Returns:
            Sequence number string

        Raises:
            ValueError: If config format is invalid
        """
        try:
            parts = config.split(":")
            if len(parts) != 2:
                msg = f"Invalid sequence config: {config}, expected format: 'start:step'"
                logger.error(f"[CustomInput] {msg}")
                raise ValueError(msg)

            start = int(parts[0])
            step = int(parts[1])

            return str(start + index * step)
        except ValueError as e:
            logger.error(f"[CustomInput] Sequence generation failed: {e}")
            # Fallback to simple index
            return str(index + 1)

    def _resolve_expression(self, expression: str, row_data: dict) -> str:
        """Resolve expression with field references and variables.

        Supports {variable} syntax with intelligent priority:
        1. Current row field values (row_data)
        2. System variables (currentDateTime, uuid32, etc.)
        3. User global variables

        Args:
            expression: Expression string like "{first_name}_{last_name}"
            row_data: Current row data dictionary

        Returns:
            Resolved string
        """
        import re

        # Find all {xxx} placeholders
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"

        def replace_placeholder(match):
            var_name = match.group(1)

            # Priority 1: Check current row data first
            if var_name in row_data:
                return str(row_data[var_name])

            # Priority 2 & 3: Try system variables and global variables via existing resolver
            try:
                resolved = self.resolve_variables_in_template_sync(f"{{{var_name}}}", "expression")
                # If resolution succeeded (not still a placeholder)
                if resolved != f"{{{var_name}}}":
                    return resolved
            except Exception:
                pass

            # Unable to resolve - keep placeholder
            return match.group(0)

        return re.sub(pattern, replace_placeholder, expression)

    def load_data(self) -> list[Data]:
        """Load custom data and return as list of Data objects.

        Generates new records based on upstream data and field configuration.
        If no upstream data is available, returns a sample record with schema for field inference.

        Returns:
            List of Data objects containing generated records
        """
        logger.info("[CustomInput] load_data called")

        try:
            # Get field schema
            field_schema = getattr(self, "field_schema", [])

            if not field_schema:
                logger.warning("[CustomInput] No field schema defined, returning empty sample")
                # Return empty sample for field inference
                return [Data(data={})]

            # Get upstream data
            upstream_data = getattr(self, "upstream_data", [])

            # Process upstream data if available
            if upstream_data:
                logger.info(f"[CustomInput] Processing {len(upstream_data)} upstream records")
                return self._process_upstream_data(upstream_data, field_schema)

            # No upstream data - return empty sample with schema for field inference
            logger.info("[CustomInput] No upstream data, returning sample record with schema")
            sample_data = {field.get("field_name"): None for field in field_schema if field.get("field_name")}
            return [Data(data=sample_data)]

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[CustomInput] Failed to load data: {error_msg}")
            logger.exception("[CustomInput] Full exception traceback:")

            translated_msg = _format_i18n(
                "components.input_output.custom_input.errors.validation_failed", error=error_msg
            )
            raise ValueError(translated_msg) from e

    async def _fetch_upstream_data_for_preview(
        self, graph_data: dict, node_id: str, sample_size: int = 10
    ) -> list[Data]:
        """Fetch upstream data for preview, bypassing GraphUtils filtering.

        This method directly finds and executes the upstream node without using
        find_upstream_node_id, which filters out "upstream_data" connections.

        Args:
            graph_data: Flow graph data containing nodes and edges
            node_id: Current node ID
            sample_size: Number of records to fetch

        Returns:
            List of Data objects from upstream node
        """
        import json

        # Manually find upstream node connected to "upstream_data" input
        edges = graph_data.get("edges", [])
        upstream_node_id = None

        logger.debug(f"[CustomInput] Searching for upstream_data connection for node '{node_id}'")
        logger.debug(f"[CustomInput] Total edges: {len(edges)}")

        for edge in edges:
            # Check if this edge targets our node
            if edge.get("target") != node_id:
                continue

            # Extract target handle
            target_handle = None

            # Method 1: Try nested format {data: {targetHandle: {fieldName}}}
            if "data" in edge:
                data_obj = edge.get("data", {})
                if isinstance(data_obj, dict):
                    target_handle_data = data_obj.get("targetHandle", {})
                    if isinstance(target_handle_data, dict):
                        target_handle = target_handle_data.get("fieldName")

            # Method 2: Try JSON string in targetHandle
            if not target_handle:
                top_level_handle = edge.get("targetHandle")
                if isinstance(top_level_handle, str):
                    if top_level_handle.startswith("{") or top_level_handle.startswith("["):
                        try:
                            cleaned_json = top_level_handle.replace("œ", '"')
                            parsed = json.loads(cleaned_json)
                            if isinstance(parsed, dict):
                                target_handle = parsed.get("fieldName")
                        except (json.JSONDecodeError, ValueError):
                            pass
                    else:
                        target_handle = top_level_handle

            logger.debug(
                f"[CustomInput] Edge: source={edge.get('source')}, "
                f"target={edge.get('target')}, targetHandle={target_handle}"
            )

            # Check if this is the upstream_data connection
            if target_handle == "upstream_data":
                upstream_node_id = edge.get("source")
                logger.info(f"[CustomInput] Found upstream_data connection from node '{upstream_node_id}'")
                break

        if not upstream_node_id:
            logger.warning("[CustomInput] No upstream node connected to 'upstream_data' input")
            return []

        # Execute the upstream node
        try:
            from lfx.graph.graph.base import Graph
            from lfx.schema import Data

            logger.debug("[CustomInput] Building temporary graph for upstream execution")

            # Transform graph data to expected format
            transformed_graph_data = self._transform_graph_data_for_execution(graph_data)

            # Create temporary graph
            temp_graph = Graph.from_payload(transformed_graph_data)
            logger.debug(f"[CustomInput] Temporary graph created with {len(temp_graph.vertices)} vertices")

            # Build the run map to establish dependency order
            temp_graph.build_run_map()

            # Get the target vertex
            target_vertex = temp_graph.get_vertex(upstream_node_id)
            if not target_vertex:
                logger.error(f"[CustomInput] Vertex '{upstream_node_id}' not found in graph")
                return []

            # Build all dependencies recursively using topological order
            vertices_to_build = []
            visited = set()

            def collect_dependencies(vertex_id: str):
                """Recursively collect all dependencies."""
                if vertex_id in visited:
                    return
                visited.add(vertex_id)

                vertex = temp_graph.get_vertex(vertex_id)
                if not vertex:
                    return

                # Get predecessor vertices (dependencies)
                predecessors = temp_graph.predecessor_map.get(vertex_id, [])
                for pred_id in predecessors:
                    collect_dependencies(pred_id)

                vertices_to_build.append(vertex_id)

            # Collect all dependencies
            collect_dependencies(upstream_node_id)

            # Build each vertex in dependency order
            for vertex_id in vertices_to_build:
                if vertex_id == upstream_node_id:
                    # Build the target vertex and get its result
                    build_result = await temp_graph.build_vertex(
                        vertex_id=vertex_id,
                        fallback_to_env_vars=True,
                        user_id=None,
                    )

                    # Extract the result from VertexBuildResult
                    built_vertex = build_result.vertex if hasattr(build_result, "vertex") else None
                    if built_vertex and hasattr(built_vertex, "results"):
                        result = built_vertex.results
                    else:
                        results_dict = build_result.results_dict if hasattr(build_result, "results_dict") else {}
                        result = list(results_dict.values())[0] if results_dict else []

                    # Unwrap result if it's a dict (like {"data": [...]})
                    if isinstance(result, dict):
                        if len(result) == 1:
                            result = list(result.values())[0]
                        elif "data" in result:
                            result = result["data"]

                    # Convert to list of Data objects
                    if not isinstance(result, list):
                        result = [result] if result else []

                    result_data = []
                    for item in result[:sample_size]:
                        if isinstance(item, Data):
                            result_data.append(item)
                        elif isinstance(item, dict):
                            result_data.append(Data(data=item))
                        else:
                            result_data.append(Data(data={"value": item}))

                    logger.info(f"[CustomInput] Successfully fetched {len(result_data)} records from upstream node")
                    return result_data
                # Build dependency vertices without capturing results
                await temp_graph.build_vertex(
                    vertex_id=vertex_id,
                    fallback_to_env_vars=True,
                    user_id=None,
                )

            logger.error("[CustomInput] Target vertex not found in dependency list")
            return []

        except Exception as e:
            logger.exception(f"[CustomInput] Failed to execute upstream node: {e}")
            return []

    def _process_upstream_data(self, upstream_data: list[Data], field_schema: list[dict]) -> list[Data]:
        """Process upstream data and generate new records based on field configuration.

        Args:
            upstream_data: List of upstream Data objects
            field_schema: Field schema configuration

        Returns:
            List of generated Data objects
        """
        result = []

        # Get localized value_source options for comparison
        from_upstream_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.from_upstream"
        )
        generate_id_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.generate_id")
        use_variable_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.use_variable"
        )
        current_time_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.current_time"
        )
        current_timestamp_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.current_timestamp"
        )
        sequence_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.sequence")
        fixed_value_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.fixed_value")
        expression_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.expression")

        for index, upstream_row in enumerate(upstream_data):
            new_record = {}
            # Extract row data for expression resolution
            row_data = upstream_row.data if hasattr(upstream_row, "data") else upstream_row

            for field_config in field_schema:
                field_name = field_config.get("field_name")
                if not field_name:
                    continue

                value_source = field_config.get("value_source", use_variable_text)
                data_type = field_config.get("data_type", "string")
                default_value = field_config.get("default_value", "")

                # Generate field value based on value_source
                if value_source == from_upstream_text:
                    # Store entire upstream row object as JSON
                    value = row_data
                    logger.debug(f"[CustomInput] Field '{field_name}': from_upstream, value type={type(value)}")

                elif value_source == generate_id_text:
                    # Generate ID based on default_value (ID type)
                    value = self._generate_id(default_value, index)
                    logger.debug(f"[CustomInput] Field '{field_name}': generate_id type={default_value}, value={value}")

                elif value_source == current_time_text:
                    # Generate current time with format
                    value = self._generate_current_time(default_value)
                    logger.debug(
                        f"[CustomInput] Field '{field_name}': current_time format={default_value}, value={value}"
                    )

                elif value_source == current_timestamp_text:
                    # Generate current timestamp
                    value = self._generate_current_timestamp(default_value)
                    logger.debug(f"[CustomInput] Field '{field_name}': current_timestamp, value={value}")

                elif value_source == sequence_text:
                    # Generate sequence number
                    value = self._generate_sequence(default_value, index)
                    logger.debug(f"[CustomInput] Field '{field_name}': sequence config={default_value}, value={value}")

                elif value_source == fixed_value_text:
                    # Use fixed value directly
                    value = default_value
                    logger.debug(f"[CustomInput] Field '{field_name}': fixed_value, value={value}")

                elif value_source == expression_text:
                    # Resolve expression with field references
                    value = self._resolve_expression(default_value, row_data)
                    logger.debug(
                        f"[CustomInput] Field '{field_name}': expression, template={default_value}, value={value}"
                    )

                else:  # use_variable_text or default
                    # Resolve variable expression
                    value = self.resolve_variables_in_template_sync(default_value, field_name)
                    logger.debug(
                        f"[CustomInput] Field '{field_name}': use_variable, template={default_value}, value={value}"
                    )

                # Convert to target data type
                try:
                    converted_value = self._convert_value(value, data_type)
                    new_record[field_name] = converted_value
                except Exception as e:
                    logger.error(
                        f"[CustomInput] Type conversion failed for field '{field_name}' (row {index + 1}): {e}"
                    )
                    raise ValueError(
                        f"Row {index + 1}, field '{field_name}': Type conversion to {data_type} failed: {e}"
                    ) from e

            result.append(Data(data=new_record))

        self.status = _format_i18n(
            "components.input_output.custom_input.status.generated_from_upstream", count=len(result)
        )
        logger.info(f"[CustomInput] Generated {len(result)} records from upstream data")

        return result

    async def _generate_preview_data(
        self, field_schema: list[dict], build_config: dict, sample_size: int = 10
    ) -> list[dict]:
        """Generate preview data simulating the real load_data execution.

        Args:
            field_schema: List of field configurations
            build_config: Build configuration containing graph data for upstream access
            sample_size: Number of sample rows to generate (default: 10)

        Returns:
            List of preview data dictionaries (for frontend table display)
        """
        preview_data = []

        # Try to get upstream data from graph
        upstream_data = []
        try:
            graph_data = build_config.get("_graph_data", {})
            node_id = build_config.get("_node_id")

            if graph_data and node_id:
                logger.info("[CustomInput] Attempting to fetch upstream data for preview...")
                # Use custom upstream fetching that bypasses GraphUtils filtering
                upstream_data = await self._fetch_upstream_data_for_preview(
                    graph_data=graph_data,
                    node_id=node_id,
                    sample_size=sample_size,
                )
                if upstream_data:
                    logger.info(f"[CustomInput] Successfully fetched {len(upstream_data)} upstream records for preview")
                else:
                    logger.info("[CustomInput] No upstream data available")
        except Exception as e:
            logger.warning(f"[CustomInput] Failed to get upstream data for preview: {e}")
            upstream_data = []

        # Check if there's a "从上游读取" field but no upstream data
        from_upstream_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.from_upstream"
        )
        has_from_upstream_field = any(field.get("value_source") == from_upstream_text for field in field_schema)

        if has_from_upstream_field and not upstream_data:
            # Don't generate fake data - show error message
            msg = i18n.t("components.input_output.custom_input.errors.preview_requires_upstream")
            raise ValueError(msg)

        # Determine row count
        row_count = len(upstream_data) if upstream_data else sample_size

        # Get localized value_source options
        from_upstream_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.from_upstream"
        )
        generate_id_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.generate_id")
        use_variable_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.use_variable"
        )
        current_time_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.current_time"
        )
        current_timestamp_text = i18n.t(
            "components.input_output.custom_input.field_schema.value_source_options.current_timestamp"
        )
        sequence_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.sequence")
        fixed_value_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.fixed_value")
        expression_text = i18n.t("components.input_output.custom_input.field_schema.value_source_options.expression")

        # Generate each row
        for index in range(row_count):
            row = {}

            # Get upstream row data if available
            upstream_row = upstream_data[index] if index < len(upstream_data) else None
            row_data = upstream_row.data if upstream_row and hasattr(upstream_row, "data") else {}

            for field_config in field_schema:
                field_name = field_config.get("field_name")
                if not field_name:
                    continue

                value_source = field_config.get("value_source", use_variable_text)
                data_type = field_config.get("data_type", "string")
                default_value = field_config.get("default_value", "")

                # Generate field value based on value_source
                try:
                    if value_source == from_upstream_text:
                        # Only use real upstream data (no simulation)
                        if upstream_row:
                            value = row_data
                        else:
                            # This should not happen due to the check above
                            msg = i18n.t("components.input_output.custom_input.errors.preview_requires_upstream")
                            raise ValueError(msg)

                    elif value_source == generate_id_text:
                        # Generate ID based on type
                        value = self._generate_id(default_value, index)

                    elif value_source == current_time_text:
                        # Generate current time with format
                        value = self._generate_current_time(default_value)

                    elif value_source == current_timestamp_text:
                        # Generate current timestamp
                        value = self._generate_current_timestamp(default_value)

                    elif value_source == sequence_text:
                        # Generate sequence number
                        value = self._generate_sequence(default_value, index)

                    elif value_source == fixed_value_text:
                        # Use fixed value directly
                        value = default_value

                    elif value_source == expression_text:
                        # Resolve expression with field references
                        # In preview, row_data may be incomplete, use what's available
                        value = self._resolve_expression(default_value, row_data)

                    else:  # use_variable_text
                        # Try to resolve variable (may fail in preview, use fallback)
                        try:
                            value = self.resolve_variables_in_template_sync(default_value, field_name)
                        except Exception:
                            # In preview mode, variable resolution may fail, use template as-is
                            value = default_value or f"{{variable_{field_name}}}"

                    # Convert for display
                    converted_value = self._convert_value_for_display(value, data_type)
                    row[field_name] = converted_value

                except Exception as e:
                    logger.warning(f"[CustomInput] Preview generation warning for field '{field_name}': {e}")
                    row[field_name] = f"<error: {str(e)[:50]}>"

            preview_data.append(row)

        return preview_data

    def _convert_value_for_display(self, value: Any, data_type: str) -> Any:
        """Convert value to format suitable for frontend table display.

        Args:
            value: Original value
            data_type: Target data type

        Returns:
            Value converted for display (JSON objects returned with special metadata)
        """
        if data_type == "json":
            # JSON type: return special object for frontend to render with icon + dialog modal
            if isinstance(value, (dict, list)):
                import json

                # Return a dict with metadata for frontend to render JSON with icon + dialog modal
                return {
                    "_type": "json",  # Special marker for frontend
                    "formatted": json.dumps(value, ensure_ascii=False, indent=2),
                    "raw": value,
                    "preview": json.dumps(value, ensure_ascii=False)[:100]
                    + ("..." if len(json.dumps(value, ensure_ascii=False)) > 100 else ""),
                }

            return str(value)

        # For other types, use standard conversion
        return self._convert_value(value, data_type)
