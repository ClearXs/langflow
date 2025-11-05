"""Helper functions for extracting fields from upstream node configurations.

This module provides utilities for extracting field information from upstream nodes
when they cannot be executed (e.g., in design-time context where upstream nodes
have dependencies that are not yet built).

This is the fallback mechanism used when get_upstream_data() fails with
"Component has not been built yet" error.
"""

from lfx.log.logger import logger


def find_and_extract_upstream_fields(
    graph_data: dict, node_id: str, input_name: str, component_name: str = "Component"
) -> list[str]:
    """Find upstream node and extract field names from its configuration.

    This is a convenience function that combines finding the upstream node
    and extracting fields in one call.

    Args:
        graph_data: Flow graph data containing nodes and edges
        node_id: Current node ID
        input_name: Name of the input to find upstream connection for
        component_name: Name of the calling component (for logging)

    Returns:
        List of field names extracted from upstream node config, or empty list if not found

    Example:
        field_names = find_and_extract_upstream_fields(
            graph_data, "my-node-id", "data_input", "MyComponent"
        )
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


def extract_fields_from_node_template(upstream_node: dict, component_name: str = "Component", graph_data: dict | None = None) -> list[str]:
    """Extract field names from upstream node template configuration.

    This is a fallback method when upstream node cannot be executed.
    It tries to extract field information from the upstream node's template configuration.

    Args:
        upstream_node: The upstream node from graph_data
        component_name: Name of the calling component (for logging)
        graph_data: The complete graph data (nodes and edges) for recursive lookups

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
            # Try to get from table_schema first
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

            # Special handling for ETLCustomInput - if no schema or data, provide common defaults
            if not field_names and upstream_node_type == "ETLCustomInput":
                logger.info(f"[{component_name}] ETLCustomInput has no schema or data configured, providing default fields")
                # Check if there are any generation rules that might give us hints about field types
                field_schema = template.get("field_schema", {}).get("value", [])
                if isinstance(field_schema, list) and field_schema:
                    field_names = [schema.get("field_name", f"field_{i+1}") for i, schema in enumerate(field_schema)]
                else:
                    # Provide sensible default field names
                    field_names = ["id", "name", "value", "type", "description", "created_at"]

        # For field value merge - extracts both upstream fields AND new merged fields
        # MUST be before the generic "Field" check below
        elif upstream_node_type == "ETLFieldValueMerge":
            logger.info(f"[{component_name}] Processing ETLFieldValueMerge node")
            logger.debug(f"[{component_name}] Template keys: {list(template.keys()) if template else 'N/A'}")

            # First, get upstream fields
            upstream_field_names = []
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
                            upstream_field_names = extract_fields_from_node_template(
                                merge_upstream_node, component_name, graph_data
                            )
                            logger.info(
                                f"[{component_name}] Extracted {len(upstream_field_names)} fields from "
                                f"ETLFieldValueMerge's upstream: {upstream_field_names}"
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
                    logger.debug(f"[{component_name}] config_value type: {type(config_value)}, length: {len(config_value) if isinstance(config_value, list) else 'N/A'}")

                    if isinstance(config_value, list):
                        new_merged_fields = [
                            merge.get("new_field")
                            for merge in config_value
                            if isinstance(merge, dict) and merge.get("new_field")
                        ]
                        logger.debug(f"[{component_name}] Extracted new_merged_fields: {new_merged_fields}")

                        if new_merged_fields:
                            logger.info(
                                f"[{component_name}] Extracted {len(new_merged_fields)} new merged fields: "
                                f"{new_merged_fields}"
                            )
                        else:
                            logger.warning(f"[{component_name}] merge_configs has {len(config_value)} items but no valid new_field found")
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
                field_names = new_merged_fields
                logger.info(
                    f"[{component_name}] ETLFieldValueMerge with drop_source_fields=True, "
                    f"returning only {len(field_names)} new fields"
                )
            else:
                # Include both upstream and new merged fields
                field_names = list(set(upstream_field_names + new_merged_fields))
                logger.info(
                    f"[{component_name}] ETLFieldValueMerge returning {len(field_names)} total fields "
                    f"({len(upstream_field_names)} upstream + {len(new_merged_fields)} merged)"
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

        # For field name mapping
        elif upstream_node_type == "ETLFieldNameMapping":
            # Extract target_field from field_mappings
            if "field_mappings" in template:
                mappings_config = template.get("field_mappings", {})
                if isinstance(mappings_config, dict):
                    config_value = mappings_config.get("value", [])
                    if isinstance(config_value, list):
                        field_names = [
                            mapping.get("target_field")
                            for mapping in config_value
                            if isinstance(mapping, dict) and mapping.get("target_field")
                        ]

            # If no field mappings configured, try to get fields from upstream of field name mapping
            if not field_names:
                logger.info(f"[{component_name}] ETLFieldNameMapping has no field_mappings, trying to get fields from its upstream")
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
                            field_names = extract_fields_from_node_template(field_mapping_upstream_node, component_name, graph_data)
                            logger.info(f"[{component_name}] Extracted {len(field_names)} fields from ETLFieldNameMapping's upstream: {field_names}")
                except Exception as e:
                    logger.debug(f"[{component_name}] Failed to extract fields from ETLFieldNameMapping's upstream: {e}")

            # If still no fields, provide some common default fields
            if not field_names:
                logger.info(f"[{component_name}] ETLFieldNameMapping has no configured fields, using common defaults")
                field_names = ["id", "name", "value", "created_at", "updated_at"]

        # For field value mapping
        elif upstream_node_type == "ETLFieldValueMapping":
            # Field value mapping doesn't change field names, just values
            # Extract field_name from mapping_rules
            if "mapping_rules" in template:
                rules_config = template.get("mapping_rules", {})
                if isinstance(rules_config, dict):
                    config_value = rules_config.get("value", [])
                    if isinstance(config_value, list):
                        field_names = [
                            rule.get("field_name")
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
                        field_names = [
                            field.get("field_name")
                            for field in config_value
                            if isinstance(field, dict) and field.get("field_name")
                        ]

        # For field unpivot
        elif upstream_node_type == "ETLFieldUnpivot":
            # Unpivot creates a standard structure with indicator and value columns
            if "indicator_column" in template:
                indicator = template.get("indicator_column", {}).get("value")
                if indicator:
                    field_names.append(indicator)
            if "value_column" in template:
                value_col = template.get("value_column", {}).get("value")
                if value_col:
                    field_names.append(value_col)
            # Also include any preserved columns
            if "preserve_columns" in template:
                preserve_config = template.get("preserve_columns", {})
                if isinstance(preserve_config, dict):
                    config_value = preserve_config.get("value", [])
                    if isinstance(config_value, list):
                        for col in config_value:
                            if isinstance(col, dict) and col.get("column_name"):
                                field_names.append(col["column_name"])

        # For field split to columns
        elif upstream_node_type == "ETLFieldSplitToColumns":
            # Extract output columns from split configuration
            if "output_columns" in template:
                output_config = template.get("output_columns", {})
                if isinstance(output_config, dict):
                    config_value = output_config.get("value", [])
                    if isinstance(config_value, list):
                        field_names = [
                            col.get("column_name")
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
                        field_names = [
                            field.get("field_name")
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
                        field_names = [
                            rule.get("field_name")
                            for rule in config_value
                            if isinstance(rule, dict) and rule.get("field_name")
                        ]

            # If cleaning_rules is empty, try to extract from filter_conditions
            if not field_names and "filter_conditions" in template:
                filter_config = template.get("filter_conditions", {})
                if isinstance(filter_config, dict):
                    filter_value = filter_config.get("value", [])
                    if isinstance(filter_value, list):
                        field_names = [
                            cond.get("field_name")
                            for cond in filter_value
                            if isinstance(cond, dict) and cond.get("field_name")
                        ]

            # If still no fields found, try to get from upstream of data cleaning
            if not field_names:
                logger.info(f"[{component_name}] ETLDataCleaning has no cleaning_rules or filter_conditions, trying to get fields from its upstream")
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
                            field_names = extract_fields_from_node_template(data_cleaning_upstream_node, component_name, graph_data)
                            logger.info(f"[{component_name}] Extracted {len(field_names)} fields from ETLDataCleaning's upstream: {field_names}")
                except Exception as e:
                    logger.debug(f"[{component_name}] Failed to extract fields from ETLDataCleaning's upstream: {e}")

            # If still no fields, provide some common default fields
            if not field_names:
                logger.info(f"[{component_name}] ETLDataCleaning has no configured fields, using common defaults")
                field_names = ["id", "name", "value", "created_at", "updated_at"]

        # For Kafka Input
        elif upstream_node_type == "ETLKafkaInput":
            # Priority 1: Extract from defined schema
            if "message_schema" in template:
                schema_config = template.get("message_schema", {})
                schema_value = schema_config.get("value", [])
                if schema_value:
                    field_names = [
                        row.get("field_name")
                        for row in schema_value
                        if row.get("field_name")
                    ]
                    logger.info(f"[{component_name}] Extracted {len(field_names)} fields from Kafka schema: {field_names}")
                    return field_names

            # Priority 2: Try to get sample data from sample_data output
            try:
                outputs = upstream_node.get("data", {}).get("node", {}).get("outputs", [])
                sample_output = next((o for o in outputs if o.get("name") == "sample_data"), None)

                if sample_output and sample_output.get("value"):
                    # Extract fields from sample data
                    sample_data = sample_output["value"]
                    if sample_data and len(sample_data) > 0:
                        first_sample = sample_data[0]
                        if hasattr(first_sample, "data"):
                            field_names = list(first_sample.data.keys())
                        elif isinstance(first_sample, dict):
                            field_names = list(first_sample.keys())

                        if field_names:
                            logger.info(f"[{component_name}] Extracted {len(field_names)} fields from Kafka sample data: {field_names}")
                            return field_names
            except Exception as e:
                logger.debug(f"[{component_name}] Failed to extract fields from Kafka sample data: {e}")

            # Priority 3: Check field_extraction_mode and output format
            field_extraction_mode = template.get("field_extraction_mode", {}).get("value", "auto")
            output_format = template.get("output_format", {}).get("value", "flattened")

            if field_extraction_mode == "schema_only":
                # Schema mode but no schema defined - return empty
                field_names = []
                logger.info(f"[{component_name}] Schema mode enabled but no schema defined: {field_names}")
            elif field_extraction_mode == "flatten_all" or output_format == "flattened":
                # Default flattened fields for Kafka messages
                field_names = [
                    "user_id", "event_type", "timestamp", "source", "payload"
                ]
                logger.info(f"[{component_name}] Using default flattened Kafka fields: {field_names}")
            else:
                # Default raw structure fields for Kafka messages
                field_names = ["value", "topic", "partition", "offset", "timestamp"]
                logger.info(f"[{component_name}] Using default raw Kafka fields: {field_names}")

        if field_names:
            logger.info(f"[{component_name}] Extracted {len(field_names)} fields from upstream config: {field_names}")
        else:
            logger.debug(
                f"[{component_name}] No fields found in upstream config. Node type: {upstream_node_type}, "
                f"Template keys: {list(template.keys()) if template else 'N/A'}"
            )

        # ============ 通用递归fallback机制 ============
        # 对于任何未明确处理的ETL组件，自动递归向上游查找字段
        if not field_names and upstream_node_type and upstream_node_type.startswith("ETL"):
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
                            field_names = extract_fields_from_node_template(
                                next_upstream_node,
                                component_name,
                                graph_data
                            )
                            if field_names:
                                logger.info(
                                    f"[{component_name}] Successfully extracted {len(field_names)} fields "
                                    f"from upstream of '{upstream_node_type}': {field_names}"
                                )
                except Exception as e:
                    logger.debug(
                        f"[{component_name}] Recursive lookup failed for '{upstream_node_type}': {e}"
                    )

        return field_names

    except Exception:  # noqa: BLE001
        logger.exception(f"[{component_name}] Failed to extract fields from upstream config")
        return []
