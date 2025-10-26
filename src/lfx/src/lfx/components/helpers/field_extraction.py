"""Helper functions for extracting fields from upstream node configurations.

This module provides utilities for extracting field information from upstream nodes
when they cannot be executed (e.g., in design-time context where upstream nodes
have dependencies that are not yet built).
"""

from lfx.log.logger import logger


def extract_fields_from_node_template(upstream_node: dict, component_name: str = "Component") -> list[str]:
    """Extract field names from upstream node template configuration.

    This is a fallback method when upstream node cannot be executed.
    It tries to extract field information from the upstream node's template configuration.

    Args:
        upstream_node: The upstream node from graph_data
        component_name: Name of the calling component (for logging)

    Returns:
        List of field names extracted from upstream config

    Supported upstream node types:
        - ETLDataEncryption: Extracts from field_configs
        - ETLDataMasking: Extracts from masking_rules
        - ETLTableInput: Extracts from table_schema or table_data
        - ETLCustomInput: Extracts from table_schema or table_data
        - ETLCSVInput: Extracts from schema or data
        - ETLExcelInput: Extracts from schema or data
        - Other data manipulation components: Extracts from their table configurations
    """
    try:
        upstream_node_data = upstream_node.get("data", {})
        upstream_node_type = upstream_node_data.get("type")

        logger.debug(f"[{component_name}] Extracting fields from upstream node type: {upstream_node_type}")

        # Extract fields based on upstream node type
        field_names = []

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
                        field_names = [
                            config.get("field")
                            for config in config_value
                            if isinstance(config, dict) and config.get("field")
                        ]

            # Try masking_rules (masking component)
            if not field_names and "masking_rules" in template:
                masking_rules = template.get("masking_rules", {})
                if isinstance(masking_rules, dict):
                    config_value = masking_rules.get("value", [])
                    if isinstance(config_value, list):
                        field_names = [
                            config.get("field")
                            for config in config_value
                            if isinstance(config, dict) and config.get("field")
                        ]

        # For table input components
        elif upstream_node_type in ["ETLTableInput", "ETLCustomInput", "ETLCSVInput", "ETLExcelInput"]:
            # Try to get from table_schema
            if "table_schema" in template:
                table_schema = template.get("table_schema", {})
                if isinstance(table_schema, dict):
                    schema_value = table_schema.get("value", [])
                    if isinstance(schema_value, list):
                        field_names = [
                            schema.get("field_name")
                            for schema in schema_value
                            if isinstance(schema, dict) and schema.get("field_name")
                        ]

            # Try to get from table_data
            if not field_names and "table_data" in template:
                table_data = template.get("table_data", {})
                if isinstance(table_data, dict):
                    data_value = table_data.get("value", [])
                    if isinstance(data_value, list) and len(data_value) > 0:
                        # Extract keys from first row
                        first_row = data_value[0]
                        if isinstance(first_row, dict):
                            field_names = list(first_row.keys())

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
                            # Try to extract field names from various possible structures
                            for item in config_value:
                                if isinstance(item, dict):
                                    # Try common field name keys
                                    for key in [
                                        "target_field",
                                        "new_field",
                                        "output_field",
                                        "field_name",
                                        "field",
                                    ]:
                                        if item.get(key):
                                            field_names.append(item[key])
                            if field_names:
                                break

        # For join/union operations
        elif upstream_node_type in ["ETLDualStreamJoin", "ETLMultiStreamUnion"]:
            # These operations output the combined fields from their inputs
            # We would need to recursively get fields from all their inputs
            # For now, we can't reliably extract this without execution
            logger.debug(f"[{component_name}] Cannot extract fields from {upstream_node_type} without execution")

        # For group_by operations
        elif upstream_node_type == "ETLGroupBy":
            # group_by outputs aggregation fields
            if "group_by_columns" in template:
                group_by_config = template.get("group_by_columns", {})
                if isinstance(group_by_config, dict):
                    config_value = group_by_config.get("value", [])
                    if isinstance(config_value, list):
                        field_names = [
                            col.get("field_name")
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
                                field_names.append(agg["output_field"])

        if field_names:
            logger.info(f"[{component_name}] Extracted {len(field_names)} fields from upstream config: {field_names}")
        else:
            logger.debug(
                f"[{component_name}] No fields found in upstream config. Node type: {upstream_node_type}, "
                f"Template keys: {list(template.keys()) if template else 'N/A'}"
            )

        return field_names

    except Exception:  # noqa: BLE001
        logger.exception(f"[{component_name}] Failed to extract fields from upstream config")
        return []
