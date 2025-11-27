"""Helper functions for extracting fields from upstream node configurations.

This module provides utilities for extracting field information from upstream nodes
when they cannot be executed (e.g., in design-time context where upstream nodes
have dependencies that are not yet built).

This is the fallback mechanism used when get_upstream_data() fails with
"Component has not been built yet" error.
"""

from lfx.log.logger import logger


def normalize_type(type_str: str | None) -> str:
    """Normalize database/SQL types to standard component types.

    Args:
        type_str: Database type (e.g., 'VARCHAR', 'INT', 'TIMESTAMP', 'integer', 'string')

    Returns:
        Normalized type: 'string', 'integer', 'float', 'boolean', 'datetime'
    """
    if not type_str:
        return "string"

    type_lower = str(type_str).lower()

    # Integer types
    if any(t in type_lower for t in ["int", "serial", "bigint", "smallint", "tinyint", "mediumint"]):
        return "integer"

    # Float types
    if any(t in type_lower for t in ["float", "double", "decimal", "numeric", "real", "money"]):
        return "float"

    # Boolean types
    if any(t in type_lower for t in ["bool", "bit"]):
        return "boolean"

    # Datetime types
    if any(t in type_lower for t in ["date", "time", "timestamp", "datetime", "interval"]):
        return "datetime"

    # Default to string for text types and unknown types
    return "string"


def _infer_type_from_value(value: any) -> str:
    """Infer field type from a sample value.

    This function can infer types from both Python objects and string representations.
    For strings, it attempts to parse them as int, float, or datetime.

    Args:
        value: Sample value to infer type from

    Returns:
        Inferred type: 'string', 'integer', 'float', 'boolean', 'datetime'
    """
    if value is None:
        return "string"

    # Check Python native types first (most accurate)
    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "float"

    # For string values, try to infer the actual data type by parsing
    if isinstance(value, str):
        # Empty string defaults to string
        if not value or value.strip() == "":
            return "string"

        value_lower = value.lower().strip()

        # Check for boolean strings
        if value_lower in ("true", "false", "yes", "no", "1", "0"):
            return "boolean"

        # Try parsing as integer
        try:
            int(value)
            return "integer"
        except ValueError:
            pass

        # Try parsing as float
        try:
            float(value)
            return "float"
        except ValueError:
            pass

        # Try detecting datetime patterns
        import re

        datetime_patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # 2024-01-01
            r"^\d{2}/\d{2}/\d{4}$",  # 01/01/2024
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO 8601
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # 2024-01-01 10:30:00
        ]
        for pattern in datetime_patterns:
            if re.match(pattern, value):
                return "datetime"

    return "string"


def find_and_extract_upstream_fields(
    graph_data: dict, node_id: str, input_name: str, component_name: str = "Component"
) -> list[dict]:
    """Find upstream node and extract field information (names and types) from its configuration.

    This is a convenience function that combines finding the upstream node
    and extracting fields in one call.

    Args:
        graph_data: Flow graph data containing nodes and edges
        node_id: Current node ID
        input_name: Name of the input to find upstream connection for
        component_name: Name of the calling component (for logging)

    Returns:
        List of field information dicts with structure:
        [
            {"name": "field1", "type": "string"},
            {"name": "field2", "type": "integer"},
            ...
        ]
        Returns empty list if no fields found.

    Example:
        fields = find_and_extract_upstream_fields(
            graph_data, "my-node-id", "data_input", "MyComponent"
        )
        # fields = [{"name": "user_id", "type": "integer"}, {"name": "name", "type": "string"}]
    """
    try:
        from lfx.custom.graph_utils import find_upstream_node_id

        # Find the upstream node ID
        upstream_node_id = find_upstream_node_id(graph_data, node_id, input_name)
        if not upstream_node_id:
            logger.debug(f"[{component_name}] No upstream node found for input '{input_name}'")
            return []

        # Find the upstream node in graph_data
        nodes = graph_data.get("nodes", [])
        upstream_node = None
        for node in nodes:
            if node.get("id") == upstream_node_id:
                upstream_node = node
                break

        if not upstream_node:
            logger.warning(f"[{component_name}] Upstream node {upstream_node_id} not found in graph data")
            return []

        # Extract fields from the upstream node
        return extract_fields_from_node_template(upstream_node, component_name, graph_data)

    except Exception:  # noqa: BLE001
        logger.exception(f"[{component_name}] Failed to find and extract upstream fields")
        return []


def extract_fields_from_node_template(
    upstream_node: dict, component_name: str = "Component", graph_data: dict | None = None
) -> list[dict]:
    """Extract field information (names and types) from upstream node template configuration.

    This is a fallback method when upstream node cannot be executed.
    It tries to extract field information from the upstream node's template configuration.

    Args:
        upstream_node: The upstream node from graph_data
        component_name: Name of the calling component (for logging)
        graph_data: The complete graph data (nodes and edges) for recursive lookups

    Returns:
        List of field information dicts with structure:
        [
            {"name": "field1", "type": "string"},
            {"name": "field2", "type": "integer"},
            ...
        ]

    Supported upstream node types:
        - ETLDataEncryption: Extracts from field_configs
        - ETLDataMasking: Extracts from masking_rules
        - ETLTableInput: Extracts from table_schema or table_data (with types from data_type)
        - ETLCustomInput: Extracts from field_schema (with types from data_type)
        - ETLCSVInput: Extracts from schema or data
        - ETLExcelInput: Extracts from schema or data
        - ETLKafkaInput: Extracts from message_schema (with types from field_type)
        - Other data manipulation components: Extracts from their table configurations
    """
    try:
        upstream_node_data = upstream_node.get("data", {})
        upstream_node_type = upstream_node_data.get("type")

        logger.debug(f"[{component_name}] Extracting fields from upstream node type: {upstream_node_type}")

        # Extract fields based on upstream node type
        # Changed from field_names to fields to store field info dicts
        fields = []

        node_config = upstream_node_data.get("node", {})
        # The actual config values are stored in the 'template' section
        template = node_config.get("template", {})

        # For encryption/masking components, extract from field_configs or masking_rules
        if upstream_node_type in ["ETLDataEncryption", "ETLDataMasking"]:
            # Try field_configs (encryption component)
            if "field_configs" in template:
                field_configs = template.get("field_configs", {})
                if isinstance(field_configs, dict):
                    config_value = field_configs.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": config.get("field"),
                                "type": config.get("field_type", "string"),  # Extract type if available
                            }
                            for config in config_value
                            if isinstance(config, dict) and config.get("field")
                        ]

            # Try masking_rules (masking component)
            if not fields and "masking_rules" in template:
                masking_rules = template.get("masking_rules", {})
                if isinstance(masking_rules, dict):
                    config_value = masking_rules.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": config.get("field"),
                                "type": config.get("field_type", "string"),  # Extract type if available
                            }
                            for config in config_value
                            if isinstance(config, dict) and config.get("field")
                        ]

        # For table input components
        elif upstream_node_type in ["ETLTableInput", "ETLCustomInput", "ETLCSVInput", "ETLExcelInput"]:
            # Try to get from field_mappings first (TableInput uses this)
            if "field_mappings" in template:
                field_mappings = template.get("field_mappings", {})
                if isinstance(field_mappings, dict):
                    mappings_value = field_mappings.get("value", [])
                    if isinstance(mappings_value, list):
                        fields = [
                            {
                                "name": mapping.get("source_field"),
                                "type": normalize_type(mapping.get("data_type")),  # Extract and normalize type
                            }
                            for mapping in mappings_value
                            if isinstance(mapping, dict) and mapping.get("source_field")
                        ]
                        if fields:
                            logger.info(
                                f"[{component_name}] Extracted {len(fields)} fields with types from field_mappings"
                            )

            # Try to get from table_schema
            if not fields and "table_schema" in template:
                table_schema = template.get("table_schema", {})
                if isinstance(table_schema, dict):
                    schema_value = table_schema.get("value", [])
                    if isinstance(schema_value, list):
                        fields = [
                            {
                                "name": schema.get("field_name"),
                                "type": normalize_type(schema.get("data_type")),  # Extract and normalize type
                            }
                            for schema in schema_value
                            if isinstance(schema, dict) and schema.get("field_name")
                        ]

            # Try to get from field_schema (CustomInput uses this)
            if not fields and "field_schema" in template:
                field_schema_config = template.get("field_schema", {})
                if isinstance(field_schema_config, dict):
                    schema_value = field_schema_config.get("value", [])
                    if isinstance(schema_value, list):
                        fields = [
                            {
                                "name": schema.get("field_name"),
                                "type": normalize_type(schema.get("data_type")),  # Extract and normalize type
                            }
                            for schema in schema_value
                            if isinstance(schema, dict) and schema.get("field_name")
                        ]

            # Try to get from table_data (infer types from data)
            if not fields and "table_data" in template:
                table_data = template.get("table_data", {})
                if isinstance(table_data, dict):
                    data_value = table_data.get("value", [])
                    if isinstance(data_value, list) and len(data_value) > 0:
                        # Extract keys from first row and infer types
                        first_row = data_value[0]
                        if isinstance(first_row, dict):
                            fields = [
                                {
                                    "name": key,
                                    "type": _infer_type_from_value(first_row[key]),  # Infer type from value
                                }
                                for key in first_row.keys()
                            ]

            # Special handling for ETLCustomInput - if no schema or data, provide common defaults
            if not fields and upstream_node_type == "ETLCustomInput":
                logger.info(
                    f"[{component_name}] ETLCustomInput has no schema or data configured, providing default fields"
                )
                # Provide sensible default fields
                fields = [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "value", "type": "string"},
                    {"name": "type", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                ]

        # For field value merge - extracts both upstream fields AND new merged fields
        # MUST be before the generic "Field" check below
        elif upstream_node_type == "ETLFieldValueMerge":
            logger.info(f"[{component_name}] Processing ETLFieldValueMerge node")
            logger.debug(f"[{component_name}] Template keys: {list(template.keys()) if template else 'N/A'}")

            # First, get upstream fields
            upstream_fields = []
            if graph_data:
                try:
                    from lfx.custom.graph_utils import find_upstream_node_id

                    merge_upstream_id = find_upstream_node_id(graph_data, upstream_node.get("id"), "data_input")
                    if merge_upstream_id:
                        upstream_nodes = graph_data.get("nodes", [])
                        merge_upstream_node = None
                        for node in upstream_nodes:
                            if node.get("id") == merge_upstream_id:
                                merge_upstream_node = node
                                break

                        if merge_upstream_node:
                            upstream_fields = extract_fields_from_node_template(
                                merge_upstream_node, component_name, graph_data
                            )
                            logger.info(
                                f"[{component_name}] Extracted {len(upstream_fields)} fields from "
                                f"ETLFieldValueMerge's upstream"
                            )
                except Exception as e:
                    logger.debug(f"[{component_name}] Failed to get upstream fields for ETLFieldValueMerge: {e}")

            # Then, add new merged fields from merge_configs
            new_merged_fields = []
            if "merge_configs" in template:
                merge_config = template.get("merge_configs", {})
                logger.debug(f"[{component_name}] merge_config type: {type(merge_config)}, content: {merge_config}")

                if isinstance(merge_config, dict):
                    config_value = merge_config.get("value", [])
                    logger.debug(
                        f"[{component_name}] config_value type: {type(config_value)}, length: {len(config_value) if isinstance(config_value, list) else 'N/A'}"
                    )

                    if isinstance(config_value, list):
                        new_merged_fields = [
                            {
                                "name": merge.get("new_field"),
                                "type": "string",  # Merged fields are typically string concatenations
                            }
                            for merge in config_value
                            if isinstance(merge, dict) and merge.get("new_field")
                        ]
                        logger.debug(f"[{component_name}] Extracted {len(new_merged_fields)} new_merged_fields")

                        if new_merged_fields:
                            logger.info(f"[{component_name}] Extracted {len(new_merged_fields)} new merged fields")
                        else:
                            logger.warning(
                                f"[{component_name}] merge_configs has {len(config_value)} items but no valid new_field found"
                            )
            else:
                logger.warning(f"[{component_name}] 'merge_configs' not found in template")

            # Combine upstream fields + new merged fields
            # Check drop_source_fields to determine if we should include original fields
            drop_source = False
            if "drop_source_fields" in template:
                drop_config = template.get("drop_source_fields", {})
                if isinstance(drop_config, dict):
                    drop_source = drop_config.get("value", False)

            if drop_source:
                # Only return new merged fields if dropping source fields
                fields = new_merged_fields
                logger.info(
                    f"[{component_name}] ETLFieldValueMerge with drop_source_fields=True, "
                    f"returning only {len(fields)} new fields"
                )
            else:
                # Include both upstream and new merged fields
                # Merge by field name, keeping unique fields
                field_map = {f["name"]: f for f in upstream_fields}
                for f in new_merged_fields:
                    field_map[f["name"]] = f
                fields = list(field_map.values())
                logger.info(
                    f"[{component_name}] ETLFieldValueMerge returning {len(fields)} total fields "
                    f"({len(upstream_fields)} upstream + {len(new_merged_fields)} merged)"
                )

        # For type conversion operations
        elif upstream_node_type == "ETLFieldTypeConversion":
            # Extract fields with their converted (target) types from type_conversions TableInput
            if "type_conversions" in template:
                type_conversions_config = template.get("type_conversions", {})
                if isinstance(type_conversions_config, dict):
                    conversions = type_conversions_config.get("value", [])
                    if isinstance(conversions, list) and conversions:
                        # Build fields list from conversion rules using target_type
                        for conversion in conversions:
                            if isinstance(conversion, dict):
                                field_name = conversion.get("field_name")
                                # Use target_type (converted type), not source_type
                                target_type = conversion.get("target_type")
                                if field_name and target_type:
                                    fields.append(
                                        {
                                            "name": field_name,
                                            "type": normalize_type(target_type),
                                        }
                                    )

                        if fields:
                            logger.info(
                                f"[{component_name}] Extracted {len(fields)} fields with converted types "
                                f"from ETLFieldTypeConversion"
                            )

                    # If type_conversions is empty or no valid conversions found,
                    # need to get fields from upstream and apply partial conversions
                    if not fields:
                        logger.debug(
                            f"[{component_name}] No type conversions configured in ETLFieldTypeConversion, "
                            f"will attempt to get fields from upstream"
                        )

        # For field manipulation components (field_split, field_pivot, etc.)
        elif upstream_node_type and "Field" in upstream_node_type:
            # These components often have field_mappings or similar configurations
            # Try common field configuration names
            for field_config_name in ["field_mappings", "mappings", "fields", "field_configs"]:
                if field_config_name in template:
                    field_config = template.get(field_config_name, {})
                    if isinstance(field_config, dict):
                        config_value = field_config.get("value", [])
                        if isinstance(config_value, list):
                            # Try to extract field info from various possible structures
                            for item in config_value:
                                if isinstance(item, dict):
                                    # Try common field name keys
                                    field_name = None
                                    for key in [
                                        "target_field",
                                        "new_field",
                                        "output_field",
                                        "field_name",
                                        "field",
                                    ]:
                                        if item.get(key):
                                            field_name = item[key]
                                            break

                                    if field_name:
                                        fields.append(
                                            {
                                                "name": field_name,
                                                "type": normalize_type(
                                                    item.get("field_type")
                                                    or item.get("data_type")
                                                    or item.get("source_type")
                                                ),
                                            }
                                        )
                            if fields:
                                break

        # For join/union operations
        elif upstream_node_type in ["ETLDualStreamJoin", "ETLMultiStreamUnion"]:
            # These operations output the combined fields from their inputs
            # We would need to recursively get fields from all their inputs
            # For now, we can't reliably extract this without execution
            logger.debug(f"[{component_name}] Cannot extract fields from {upstream_node_type} without execution")

        # For group_by operations
        elif upstream_node_type == "ETLGroupBy":
            # group_by outputs group columns + aggregation fields
            if "group_by_columns" in template:
                group_by_config = template.get("group_by_columns", {})
                if isinstance(group_by_config, dict):
                    config_value = group_by_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": col.get("field_name"),
                                "type": col.get("field_type", "string"),  # Group by preserves type
                            }
                            for col in config_value
                            if isinstance(col, dict) and col.get("field_name")
                        ]

            # Also try to get aggregation fields
            if "aggregations" in template:
                agg_config = template.get("aggregations", {})
                if isinstance(agg_config, dict):
                    config_value = agg_config.get("value", [])
                    if isinstance(config_value, list):
                        for agg in config_value:
                            if isinstance(agg, dict) and agg.get("output_field"):
                                # Aggregation type depends on function
                                agg_func = agg.get("function", "").lower()
                                if agg_func in ["count", "count_distinct"]:
                                    agg_type = "integer"
                                elif agg_func in ["sum", "avg", "mean", "stddev", "variance"]:
                                    agg_type = "float"
                                else:
                                    agg_type = "string"  # min/max preserve type, default to string

                                fields.append(
                                    {
                                        "name": agg["output_field"],
                                        "type": agg_type,
                                    }
                                )

        # For field name mapping
        elif upstream_node_type == "ETLFieldNameMapping":
            # Extract target_field from field_mappings
            if "field_mappings" in template:
                mappings_config = template.get("field_mappings", {})
                if isinstance(mappings_config, dict):
                    config_value = mappings_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": mapping.get("target_field"),
                                "type": normalize_type(mapping.get("source_type")),  # Extract type from mapping
                            }
                            for mapping in config_value
                            if isinstance(mapping, dict) and mapping.get("target_field")
                        ]

            # If no field mappings configured, try to get fields from upstream of field name mapping
            if not fields:
                logger.info(
                    f"[{component_name}] ETLFieldNameMapping has no field_mappings, trying to get fields from its upstream"
                )
                try:
                    # Recursively try to get fields from the upstream of field name mapping
                    from lfx.custom.graph_utils import find_upstream_node_id

                    # Find the upstream of ETLFieldNameMapping
                    field_mapping_upstream_id = find_upstream_node_id(graph_data, upstream_node.get("id"), "data_input")
                    if field_mapping_upstream_id:
                        # Find the upstream node in graph_data
                        upstream_nodes = graph_data.get("nodes", [])
                        field_mapping_upstream_node = None
                        for node in upstream_nodes:
                            if node.get("id") == field_mapping_upstream_id:
                                field_mapping_upstream_node = node
                                break

                        if field_mapping_upstream_node:
                            # Extract fields from the upstream of field name mapping
                            fields = extract_fields_from_node_template(
                                field_mapping_upstream_node, component_name, graph_data
                            )
                            logger.info(
                                f"[{component_name}] Extracted {len(fields)} fields from ETLFieldNameMapping's upstream"
                            )
                except Exception as e:
                    logger.debug(
                        f"[{component_name}] Failed to extract fields from ETLFieldNameMapping's upstream: {e}"
                    )

            # If still no fields, provide some common default fields
            if not fields:
                logger.info(f"[{component_name}] ETLFieldNameMapping has no configured fields, using common defaults")
                fields = [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "value", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"},
                ]

        # For field value mapping
        elif upstream_node_type == "ETLFieldValueMapping":
            # Field value mapping doesn't change field names, just values
            # Extract field_name from mapping_rules
            if "mapping_rules" in template:
                rules_config = template.get("mapping_rules", {})
                if isinstance(rules_config, dict):
                    config_value = rules_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": rule.get("field_name"),
                                "type": rule.get("field_type", "string"),
                            }
                            for rule in config_value
                            if isinstance(rule, dict) and rule.get("field_name")
                        ]

        # For field pivot
        elif upstream_node_type == "ETLFieldPivot":
            # Pivot operation creates new column names based on pivot values
            # We can try to extract configured output columns, but this is limited
            # without actual data execution
            if "output_fields" in template:
                output_config = template.get("output_fields", {})
                if isinstance(output_config, dict):
                    config_value = output_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": field.get("field_name"),
                                "type": field.get("field_type", "string"),
                            }
                            for field in config_value
                            if isinstance(field, dict) and field.get("field_name")
                        ]

        # For field unpivot
        elif upstream_node_type == "ETLFieldUnpivot":
            # Unpivot creates a standard structure with indicator and value columns
            if "indicator_column" in template:
                indicator = template.get("indicator_column", {}).get("value")
                if indicator:
                    fields.append({"name": indicator, "type": "string"})  # Indicator is string
            if "value_column" in template:
                value_col = template.get("value_column", {}).get("value")
                if value_col:
                    fields.append({"name": value_col, "type": "string"})  # Value column type varies, default string
            # Also include any preserved columns
            if "preserve_columns" in template:
                preserve_config = template.get("preserve_columns", {})
                if isinstance(preserve_config, dict):
                    config_value = preserve_config.get("value", [])
                    if isinstance(config_value, list):
                        for col in config_value:
                            if isinstance(col, dict) and col.get("column_name"):
                                fields.append(
                                    {
                                        "name": col["column_name"],
                                        "type": col.get("column_type", "string"),
                                    }
                                )

        # For field split to columns
        elif upstream_node_type == "ETLFieldSplitToColumns":
            # Extract output columns from split configuration
            if "output_columns" in template:
                output_config = template.get("output_columns", {})
                if isinstance(output_config, dict):
                    config_value = output_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": col.get("column_name"),
                                "type": "string",  # Split columns are strings
                            }
                            for col in config_value
                            if isinstance(col, dict) and col.get("column_name")
                        ]

        # For deduplication
        elif upstream_node_type == "ETLDeduplication":
            # Deduplication preserves all fields from input
            # Try to extract from group_by_fields
            if "group_by_fields" in template:
                dedup_config = template.get("group_by_fields", {})
                if isinstance(dedup_config, dict):
                    config_value = dedup_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": field.get("field_name"),
                                "type": field.get("field_type", "string"),
                            }
                            for field in config_value
                            if isinstance(field, dict) and field.get("field_name")
                        ]

        # For data cleaning
        elif upstream_node_type == "ETLDataCleaning":
            # Data cleaning preserves field names but transforms values
            # Extract from cleaning_rules first
            if "cleaning_rules" in template:
                cleaning_config = template.get("cleaning_rules", {})
                if isinstance(cleaning_config, dict):
                    config_value = cleaning_config.get("value", [])
                    if isinstance(config_value, list):
                        fields = [
                            {
                                "name": rule.get("field_name"),
                                "type": rule.get("field_type", "string"),
                            }
                            for rule in config_value
                            if isinstance(rule, dict) and rule.get("field_name")
                        ]

            # If cleaning_rules is empty, try to extract from filter_conditions
            if not fields and "filter_conditions" in template:
                filter_config = template.get("filter_conditions", {})
                if isinstance(filter_config, dict):
                    filter_value = filter_config.get("value", [])
                    if isinstance(filter_value, list):
                        fields = [
                            {
                                "name": cond.get("field_name"),
                                "type": cond.get("field_type", "string"),
                            }
                            for cond in filter_value
                            if isinstance(cond, dict) and cond.get("field_name")
                        ]

            # If still no fields found, try to get from upstream of data cleaning
            if not fields:
                logger.info(
                    f"[{component_name}] ETLDataCleaning has no cleaning_rules or filter_conditions, trying to get fields from its upstream"
                )
                try:
                    # Recursively try to get fields from the upstream of data cleaning
                    from lfx.custom.graph_utils import find_upstream_node_id

                    # Find the upstream of ETLDataCleaning
                    data_cleaning_upstream_id = find_upstream_node_id(graph_data, upstream_node.get("id"), "data_input")
                    if data_cleaning_upstream_id:
                        # Find the upstream node in graph_data
                        upstream_nodes = graph_data.get("nodes", [])
                        data_cleaning_upstream_node = None
                        for node in upstream_nodes:
                            if node.get("id") == data_cleaning_upstream_id:
                                data_cleaning_upstream_node = node
                                break

                        if data_cleaning_upstream_node:
                            # Extract fields from the upstream of data cleaning
                            fields = extract_fields_from_node_template(
                                data_cleaning_upstream_node, component_name, graph_data
                            )
                            logger.info(
                                f"[{component_name}] Extracted {len(fields)} fields from ETLDataCleaning's upstream"
                            )
                except Exception as e:
                    logger.debug(f"[{component_name}] Failed to extract fields from ETLDataCleaning's upstream: {e}")

            # If still no fields, provide some common default fields
            if not fields:
                logger.info(f"[{component_name}] ETLDataCleaning has no configured fields, using common defaults")
                fields = [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "value", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"},
                ]

        # For API Input
        elif upstream_node_type == "ETLAPIInput":
            # ETLAPIInput dynamically fetches data from API
            # We cannot predict the exact schema without execution
            # Try to get from upstream_data if available (after execution)
            if "upstream_data" in template:
                upstream_data_config = template.get("upstream_data", {})
                upstream_data_value = upstream_data_config.get("value")
                if upstream_data_value and isinstance(upstream_data_value, list) and len(upstream_data_value) > 0:
                    # Extract fields from actual data sample
                    first_sample = upstream_data_value[0]
                    if isinstance(first_sample, dict):
                        if "data" in first_sample and isinstance(first_sample["data"], dict):
                            sample_dict = first_sample["data"]
                        else:
                            sample_dict = first_sample

                        fields = [
                            {
                                "name": key,
                                "type": _infer_type_from_value(value),
                            }
                            for key, value in sample_dict.items()
                        ]
                        logger.info(f"[{component_name}] Extracted {len(fields)} fields from API Input sample data")
                        return fields

            # If no sample data available, return generic placeholder fields
            logger.info(f"[{component_name}] ETLAPIInput has no sample data, providing generic default fields")
            fields = [
                {"name": "id", "type": "string"},
                {"name": "data", "type": "string"},
                {"name": "timestamp", "type": "datetime"},
                {"name": "status", "type": "string"},
            ]

        # For Kafka Input
        elif upstream_node_type == "ETLKafkaInput":
            # Priority 1: Extract from defined schema
            if "message_schema" in template:
                schema_config = template.get("message_schema", {})
                schema_value = schema_config.get("value", [])
                if schema_value:
                    fields = [
                        {
                            "name": row.get("field_name"),
                            "type": normalize_type(row.get("field_type")),  # Kafka uses field_type
                        }
                        for row in schema_value
                        if row.get("field_name")
                    ]
                    logger.info(f"[{component_name}] Extracted {len(fields)} fields from Kafka schema")
                    return fields

            # Priority 2: Try to get sample data from sample_data output
            try:
                outputs = upstream_node.get("data", {}).get("node", {}).get("outputs", [])
                sample_output = next((o for o in outputs if o.get("name") == "sample_data"), None)

                if sample_output and sample_output.get("value"):
                    # Extract fields from sample data
                    sample_data = sample_output["value"]
                    if sample_data and len(sample_data) > 0:
                        first_sample = sample_data[0]
                        sample_dict = None
                        if hasattr(first_sample, "data"):
                            sample_dict = first_sample.data
                        elif isinstance(first_sample, dict):
                            sample_dict = first_sample

                        if sample_dict:
                            fields = [
                                {
                                    "name": key,
                                    "type": _infer_type_from_value(value),
                                }
                                for key, value in sample_dict.items()
                            ]
                            logger.info(f"[{component_name}] Extracted {len(fields)} fields from Kafka sample data")
                            return fields
            except Exception as e:
                logger.debug(f"[{component_name}] Failed to extract fields from Kafka sample data: {e}")

            # Priority 3: Check field_extraction_mode and output format
            field_extraction_mode = template.get("field_extraction_mode", {}).get("value", "auto")
            output_format = template.get("output_format", {}).get("value", "flattened")

            if field_extraction_mode == "schema_only":
                # Schema mode but no schema defined - return empty
                fields = []
                logger.info(f"[{component_name}] Schema mode enabled but no schema defined")
            elif field_extraction_mode == "flatten_all" or output_format == "flattened":
                # Default flattened fields for Kafka messages
                fields = [
                    {"name": "user_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "timestamp", "type": "datetime"},
                    {"name": "source", "type": "string"},
                    {"name": "payload", "type": "string"},
                ]
                logger.info(f"[{component_name}] Using default flattened Kafka fields")
            else:
                # Default raw structure fields for Kafka messages
                fields = [
                    {"name": "value", "type": "string"},
                    {"name": "topic", "type": "string"},
                    {"name": "partition", "type": "integer"},
                    {"name": "offset", "type": "integer"},
                    {"name": "timestamp", "type": "datetime"},
                ]
                logger.info(f"[{component_name}] Using default raw Kafka fields")

        # For ConditionalRouter - passthrough fields from upstream
        elif upstream_node_type == "ConditionalRouter":
            # ConditionalRouter filters data but doesn't change field structure
            # Get fields from its upstream data_input
            if graph_data:
                logger.info(f"[{component_name}] ConditionalRouter detected, extracting fields from its upstream")
                try:
                    from lfx.custom.graph_utils import find_upstream_node_id

                    router_upstream_id = find_upstream_node_id(graph_data, upstream_node.get("id"), "data_input")
                    if router_upstream_id:
                        upstream_nodes = graph_data.get("nodes", [])
                        router_upstream_node = None
                        for node in upstream_nodes:
                            if node.get("id") == router_upstream_id:
                                router_upstream_node = node
                                break

                        if router_upstream_node:
                            fields = extract_fields_from_node_template(router_upstream_node, component_name, graph_data)
                            logger.info(
                                f"[{component_name}] Extracted {len(fields)} fields from ConditionalRouter's upstream"
                            )
                except Exception as e:
                    logger.debug(f"[{component_name}] Failed to extract fields from ConditionalRouter's upstream: {e}")

        # For DataOperations - calculate output fields based on operation type
        elif upstream_node_type == "DataOperations":
            logger.info(f"[{component_name}] DataOperations detected, analyzing operation type")

            # First, check if output fields were already calculated during update_build_config
            if "_output_fields" in template:
                output_fields = template.get("_output_fields", {}).get("value")
                if output_fields and isinstance(output_fields, list):
                    fields = output_fields
                    logger.info(
                        f"[{component_name}] Using pre-calculated output fields from DataOperations: {len(fields)} fields"
                    )
                    return fields

            # Otherwise, try to calculate based on operation and upstream
            if "operations" in template:
                operations_config = template.get("operations", {})
                if isinstance(operations_config, dict):
                    operations_value = operations_config.get("value", [])
                    if isinstance(operations_value, list) and len(operations_value) > 0:
                        operation_name = (
                            operations_value[0].get("name", "") if isinstance(operations_value[0], dict) else ""
                        )

                        logger.debug(f"[{component_name}] DataOperations operation: {operation_name}")

                        # Get upstream fields first
                        upstream_fields = []
                        if graph_data:
                            try:
                                from lfx.custom.graph_utils import find_upstream_node_id

                                data_ops_upstream_id = find_upstream_node_id(
                                    graph_data, upstream_node.get("id"), "data"
                                )
                                if data_ops_upstream_id:
                                    upstream_nodes = graph_data.get("nodes", [])
                                    data_ops_upstream_node = None
                                    for node in upstream_nodes:
                                        if node.get("id") == data_ops_upstream_id:
                                            data_ops_upstream_node = node
                                            break

                                    if data_ops_upstream_node:
                                        upstream_fields = extract_fields_from_node_template(
                                            data_ops_upstream_node, component_name, graph_data
                                        )
                                        logger.info(
                                            f"[{component_name}] Extracted {len(upstream_fields)} fields from DataOperations upstream"
                                        )
                            except Exception as e:
                                logger.debug(
                                    f"[{component_name}] Failed to get upstream fields for DataOperations: {e}"
                                )

                        # Calculate output fields based on operation type
                        if upstream_fields:
                            # Map localized operation names to internal names
                            import i18n

                            operation_map = {
                                i18n.t("components.processing.data_operations.operations.select_keys"): "Select Keys",
                                i18n.t("components.processing.data_operations.operations.literal_eval"): "Literal Eval",
                                i18n.t("components.processing.data_operations.operations.combine"): "Combine",
                                i18n.t(
                                    "components.processing.data_operations.operations.filter_values"
                                ): "Filter Values",
                                i18n.t(
                                    "components.processing.data_operations.operations.append_update"
                                ): "Append or Update",
                                i18n.t("components.processing.data_operations.operations.remove_keys"): "Remove Keys",
                                i18n.t("components.processing.data_operations.operations.rename_keys"): "Rename Keys",
                                i18n.t(
                                    "components.processing.data_operations.operations.path_selection"
                                ): "Path Selection",
                                i18n.t(
                                    "components.processing.data_operations.operations.jq_expression"
                                ): "JQ Expression",
                            }
                            internal_operation = operation_map.get(operation_name, operation_name)

                            if internal_operation == "Select Keys":
                                # Only selected keys are output
                                select_keys_config = template.get("select_keys_input", {})
                                select_keys_value = select_keys_config.get("value", [])
                                if select_keys_value:
                                    selected_names = set(select_keys_value)
                                    fields = [f for f in upstream_fields if f["name"] in selected_names]
                                else:
                                    fields = upstream_fields

                            elif internal_operation == "Remove Keys":
                                # All fields except removed keys
                                remove_keys_config = template.get("remove_keys_input", {})
                                remove_keys_value = remove_keys_config.get("value", [])
                                if remove_keys_value:
                                    removed_names = set(remove_keys_value)
                                    fields = [f for f in upstream_fields if f["name"] not in removed_names]
                                else:
                                    fields = upstream_fields

                            elif internal_operation == "Rename Keys":
                                # Fields with renamed names
                                rename_keys_config = template.get("rename_keys_input", {})
                                rename_keys_value = rename_keys_config.get("value", {})
                                if rename_keys_value and isinstance(rename_keys_value, dict):
                                    fields = []
                                    for field in upstream_fields:
                                        new_name = rename_keys_value.get(field["name"], field["name"])
                                        fields.append({"name": new_name, "type": field["type"]})
                                else:
                                    fields = upstream_fields

                            elif internal_operation == "Append or Update":
                                # Original fields + new fields
                                append_data_config = template.get("append_update_data", {})
                                append_data_value = append_data_config.get("value", {})
                                fields = upstream_fields.copy()
                                if append_data_value and isinstance(append_data_value, dict):
                                    existing_names = {f["name"] for f in fields}
                                    for key, value in append_data_value.items():
                                        if key not in existing_names:
                                            fields.append({"name": key, "type": _infer_type_from_value(value)})

                            elif internal_operation in ["Literal Eval", "Filter Values", "Combine"]:
                                # All fields preserved
                                fields = upstream_fields

                            elif internal_operation in ["Path Selection", "JQ Expression"]:
                                # Output depends on path/query - return generic result
                                fields = [{"name": "result", "type": "string"}]

                            else:
                                # Default: return all upstream fields
                                fields = upstream_fields

                            if fields:
                                logger.info(
                                    f"[{component_name}] Calculated {len(fields)} output fields for DataOperations '{internal_operation}'"
                                )

        if fields:
            logger.info(f"[{component_name}] Extracted {len(fields)} fields from upstream config")
        else:
            logger.debug(
                f"[{component_name}] No fields found in upstream config. Node type: {upstream_node_type}, "
                f"Template keys: {list(template.keys()) if template else 'N/A'}"
            )

        # ============ 通用递归fallback机制 ============
        # 对于任何未明确处理的ETL组件，自动递归向上游查找字段
        if not fields and upstream_node_type and upstream_node_type.startswith("ETL"):
            if graph_data:
                logger.info(
                    f"[{component_name}] No specific field extraction logic for '{upstream_node_type}', "
                    f"attempting recursive upstream lookup"
                )
                try:
                    from lfx.custom.graph_utils import find_upstream_node_id

                    # 查找当前节点的上游节点
                    upstream_id = find_upstream_node_id(graph_data, upstream_node.get("id"), "data_input")
                    if upstream_id:
                        # 在graph_data中找到上游节点
                        upstream_nodes = graph_data.get("nodes", [])
                        next_upstream_node = None
                        for node in upstream_nodes:
                            if node.get("id") == upstream_id:
                                next_upstream_node = node
                                break

                        if next_upstream_node:
                            # 递归提取上游节点的字段
                            fields = extract_fields_from_node_template(next_upstream_node, component_name, graph_data)
                            if fields:
                                logger.info(
                                    f"[{component_name}] Successfully extracted {len(fields)} fields "
                                    f"from upstream of '{upstream_node_type}'"
                                )
                except Exception as e:
                    logger.debug(f"[{component_name}] Recursive lookup failed for '{upstream_node_type}': {e}")

        return fields

    except Exception:  # noqa: BLE001
        logger.exception(f"[{component_name}] Failed to extract fields from upstream config")
        return []
