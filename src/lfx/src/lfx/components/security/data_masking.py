from typing import Any

import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data


class ETLDataMaskingComponent(Component):
    display_name = i18n.t("components.security.data_masking.display_name")
    description = i18n.t("components.security.data_masking.description")
    icon = "eye-off"
    name = "ETLDataMasking"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.security.data_masking.data_input.display_name"),
            info=i18n.t("components.security.data_masking.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="masking_rules",
            display_name=i18n.t("components.security.data_masking.masking_rules.display_name"),
            info=i18n.t("components.security.data_masking.masking_rules.info"),
            table_schema=[
                {
                    "name": "field",
                    "display_name": i18n.t("components.security.data_masking.masking_rules.field"),
                    "type": "str",
                    "formatter": "text",
                    "required": True,
                    "description": i18n.t("components.security.data_masking.masking_rules.field_desc"),
                },
                {
                    "name": "rule_id",
                    "display_name": i18n.t("components.security.data_masking.masking_rules.rule_id"),
                    "type": "int",
                    "formatter": "text",
                    "options": [],  # 动态填充
                    "options_metadata": [],  # 动态填充
                    "required": True,
                    "description": i18n.t("components.security.data_masking.masking_rules.rule_id_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.security.data_masking.masking_rules.load_fields_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.security.data_masking.outputs.data.display_name"),
            method="mask_data",
        ),
        Output(
            name="masking_stats",
            display_name=i18n.t("components.security.data_masking.outputs.masking_stats.display_name"),
            method="get_masking_stats",
        ),
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates for field loading.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[DataMasking] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle "load_fields" button click
        if field_name == "masking_rules" and action == "load_fields":
            logger.info("[DataMasking] Field and rule loading triggered")

            try:
                # 1. Load field names from upstream data
                field_names = await self._load_upstream_fields(build_config)

                # 2. Load masking rules from data security service
                masking_rules = await self._load_masking_rules()
                if masking_rules:
                    build_config["masking_rules"]["table_schema"][1]["options"] = [
                        int(rule["id"]) for rule in masking_rules
                    ]
                    build_config["masking_rules"]["table_schema"][1]["options_metadata"] = [
                        {"value": int(rule["id"]), "label": rule["ruleName"]} for rule in masking_rules
                    ]
                else:
                    build_config["masking_rules"]["table_schema"][1]["options"] = []
                    build_config["masking_rules"]["table_schema"][1]["options_metadata"] = []

                # 3. Replace table with loaded fields (deduplicated, rule_id left empty)
                unique_fields = list(dict.fromkeys(field_names))  # Preserve order while deduplicating
                build_config["masking_rules"]["value"] = [{"field": field_name} for field_name in unique_fields]

                logger.info(
                    f"[DataMasking] Replaced table with {len(unique_fields)} unique fields "
                    f"and {len(masking_rules)} rules available"
                )

                self.status = i18n.t(
                    "components.security.data_masking.status.load_success",
                    fields_count=len(unique_fields),
                    rules_count=len(masking_rules) if masking_rules else 0,
                )

            except ValueError as e:
                error_msg = str(e)
                logger.warning(f"[DataMasking] Field loading warning: {error_msg}")

                # Fallback: try to extract fields from upstream node config
                try:
                    logger.info("[DataMasking] Attempting fallback: extracting fields from upstream node config")
                    field_names = self._extract_fields_from_upstream_config(
                        build_config, build_config.get("_graph_data", {}), build_config.get("_node_id")
                    )

                    if field_names:
                        # Still try to load masking rules even in fallback mode
                        try:
                            masking_rules = await self._load_masking_rules()
                            if masking_rules:
                                build_config["masking_rules"]["table_schema"][1]["options"] = [
                                    int(rule["id"]) for rule in masking_rules
                                ]
                                build_config["masking_rules"]["table_schema"][1]["options_metadata"] = [
                                    {"value": int(rule["id"]), "label": rule["ruleName"]} for rule in masking_rules
                                ]
                                logger.info(f"[DataMasking] Loaded {len(masking_rules)} masking rules in fallback mode")
                            else:
                                build_config["masking_rules"]["table_schema"][1]["options"] = []
                                build_config["masking_rules"]["table_schema"][1]["options_metadata"] = []
                        except Exception:  # noqa: BLE001
                            logger.exception("[DataMasking] Failed to load masking rules in fallback mode")
                            build_config["masking_rules"]["table_schema"][1]["options"] = []
                            build_config["masking_rules"]["table_schema"][1]["options_metadata"] = []

                        # Replace table with loaded fields (deduplicated, rule_id left empty)
                        unique_fields = list(dict.fromkeys(field_names))  # Preserve order while deduplicating
                        build_config["masking_rules"]["value"] = [{"field": field_name} for field_name in unique_fields]

                        logger.info(f"[DataMasking] Replaced table with {len(unique_fields)} fields (from config)")

                        masking_rules_count = len(build_config["masking_rules"]["table_schema"][1].get("options", []))
                        self.status = i18n.t(
                            "components.security.data_masking.status.load_success",
                            fields_count=len(unique_fields),
                            rules_count=masking_rules_count,
                        )
                    else:
                        self.status = i18n.t("components.security.data_masking.errors.load_failed", error=error_msg)
                except Exception:  # noqa: BLE001
                    logger.exception("[DataMasking] Fallback also failed")
                    self.status = i18n.t("components.security.data_masking.errors.load_failed", error=error_msg)

            except Exception:  # noqa: BLE001
                logger.exception("[DataMasking] Field loading failed with unexpected error")
                self.status = i18n.t("components.security.data_masking.errors.graph_not_available")

        return build_config

    async def _load_upstream_fields(self, build_config: dict) -> list[str]:
        """Load field names from upstream data.

        Args:
            build_config: Build configuration

        Returns:
            List of field names
        """
        # Get graph_data and node_id from build_config
        graph_data = build_config.get("_graph_data", {})
        node_id = build_config.get("_node_id")

        # If not in build_config, try to get from self.graph
        if not graph_data and hasattr(self, "graph") and self.graph is not None:
            if hasattr(self.graph, "data"):
                graph_data = self.graph.data
            else:
                logger.warning("[DataMasking] PlaceholderGraph detected - no graph data available")

        if not graph_data:
            logger.warning("[DataMasking] No graph data available")
            return []

        # Fetch upstream data
        upstream_data = await self.get_upstream_data(
            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
        )

        if not upstream_data:
            logger.warning("[DataMasking] No data returned from upstream node")
            return []

        # Extract field names
        field_names = self._extract_field_names(upstream_data)

        if not field_names:
            logger.warning("[DataMasking] No fields extracted from upstream data")
            return []

        logger.debug(f"[DataMasking] Extracted {len(field_names)} field names: {field_names}")
        return field_names

    async def _load_masking_rules(self) -> list[dict]:
        """Load masking rules from data security service.

        Returns:
            List of masking rules
        """
        try:
            from lfx.services.deps import get_data_security_client

            client = get_data_security_client()
            if client is None:
                logger.warning("[DataMasking] Data security client not available")
                return []

            rules = await client.get_protection_rules(rule_type="MASKING")
            logger.info(f"[DataMasking] Loaded {len(rules)} masking rules")
            return rules

        except Exception as e:
            logger.exception(f"[DataMasking] Failed to load masking rules: {e}")
            return []

    def _extract_field_names(self, data_list: list[Data]) -> list[str]:
        """Extract field names from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of field names
        """
        try:
            if not data_list:
                return []

            # Get first record to extract field names
            first_record = data_list[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[DataMasking] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[DataMasking] Expected dict, got {type(data_dict)}")
                return []

            field_names = list(data_dict.keys())
            logger.debug(f"[DataMasking] Extracted {len(field_names)} field names: {field_names}")
            return field_names

        except Exception:  # noqa: BLE001
            logger.exception("[DataMasking] Failed to extract field names")
            return []

    def _extract_fields_from_upstream_config(self, build_config: dict, graph_data: dict, node_id: str) -> list[str]:
        """Extract field names from upstream node configuration.

        This is a fallback method when upstream node cannot be executed.
        It tries to extract field information from the upstream node's configuration.

        Args:
            build_config: Current build configuration
            graph_data: Flow graph data
            node_id: Current node ID

        Returns:
            List of field names extracted from upstream config
        """
        try:
            from lfx.custom.graph_utils import find_upstream_node_id

            # Find upstream node
            upstream_node_id = find_upstream_node_id(graph_data, node_id, "data_input")
            if not upstream_node_id:
                logger.warning("[DataMasking] No upstream node found")
                return []

            # Find upstream node in graph_data
            nodes = graph_data.get("nodes", [])
            upstream_node = None
            for node in nodes:
                if node.get("id") == upstream_node_id:
                    upstream_node = node
                    break

            if not upstream_node:
                logger.warning(f"[DataMasking] Upstream node {upstream_node_id} not found in graph data")
                return []

            # Debug: log the entire upstream node structure
            import json

            logger.debug(
                f"[DataMasking] Full upstream node structure: {json.dumps(upstream_node, indent=2, default=str)}"
            )

            upstream_node_data = upstream_node.get("data", {})
            upstream_node_type = upstream_node_data.get("type")

            logger.info(f"[DataMasking] Upstream node type: {upstream_node_type}")
            logger.debug(f"[DataMasking] Upstream node data keys: {list(upstream_node_data.keys())}")

            # Extract fields based on upstream node type
            field_names = []

            # For encryption/masking components, extract from field_configs
            if upstream_node_type in ["ETLDataEncryption", "ETLDataMasking"]:
                # Look for field_configs or masking_rules in node data
                node_config = upstream_node_data.get("node", {})
                logger.debug(f"[DataMasking] Node config keys: {list(node_config.keys())}")

                # The actual config values are stored in the 'template' section
                template = node_config.get("template", {})
                logger.debug(f"[DataMasking] Template keys: {list(template.keys())}")

                # Try field_configs (encryption component)
                if "field_configs" in template:
                    field_configs = template.get("field_configs", {})
                    logger.debug(f"[DataMasking] Found field_configs in template: {field_configs}")
                    if isinstance(field_configs, dict):
                        config_value = field_configs.get("value", [])
                        logger.debug(f"[DataMasking] field_configs.value: {config_value}")
                        if isinstance(config_value, list):
                            field_names = [
                                config.get("field")
                                for config in config_value
                                if isinstance(config, dict) and config.get("field")
                            ]

                # Try masking_rules (masking component)
                if not field_names and "masking_rules" in template:
                    masking_rules = template.get("masking_rules", {})
                    logger.debug(f"[DataMasking] Found masking_rules in template: {masking_rules}")
                    if isinstance(masking_rules, dict):
                        config_value = masking_rules.get("value", [])
                        logger.debug(f"[DataMasking] masking_rules.value: {config_value}")
                        if isinstance(config_value, list):
                            field_names = [
                                config.get("field")
                                for config in config_value
                                if isinstance(config, dict) and config.get("field")
                            ]

                if not field_names:
                    logger.debug(
                        f"[DataMasking] No field_configs or masking_rules found in template. "
                        f"Available keys: {list(template.keys())}"
                    )

            # For table components or other data sources
            elif upstream_node_type in ["ETLTableInput", "ETLCustomInput", "ETLCSVInput", "ETLExcelInput"]:
                node_config = upstream_node_data.get("node", {})
                template = node_config.get("template", {})

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

            if field_names:
                logger.info(f"[DataMasking] Extracted {len(field_names)} fields from upstream config: {field_names}")
            else:
                logger.warning("[DataMasking] No fields found in upstream config")

            return field_names

        except Exception:  # noqa: BLE001
            logger.exception("[DataMasking] Failed to extract fields from upstream config")
            return []

    async def mask_data(self) -> list[Data]:
        """Apply masking rules to data using external service."""
        try:
            logger.info("[DataMasking] Starting data masking")

            if not self.data_input or not self.masking_rules:
                raise ValueError(i18n.t("components.security.data_masking.errors.missing_config"))

            # Convert to DataFrame
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])

            logger.info(f"[DataMasking] Processing {len(df)} records with {len(self.masking_rules)} masking rules")

            from lfx.services.deps import get_data_security_client

            client = get_data_security_client()
            if client is None:
                raise ValueError(i18n.t("components.security.data_masking.errors.service_unavailable"))

            # Collect all masking rules for batch processing
            batch_requests = []
            field_mapping = []  # To map requests back to DataFrame positions

            for rule_idx, rule in enumerate(self.masking_rules):
                field = rule.get("field", "").strip()
                rule_id = rule.get("rule_id")

                if not field or not rule_id:
                    logger.warning(f"[DataMasking] Skipping empty rule: {rule}")
                    continue

                if field not in df.columns:
                    logger.warning(f"[DataMasking] Field '{field}' not found in data, skipping")
                    continue

                # Extract non-null values for batch processing
                mask = df[field].notnull()
                values_to_mask = df.loc[mask, field].astype(str).tolist()

                if not values_to_mask:
                    logger.debug(f"[DataMasking] No values to mask in field '{field}'")
                    continue

                logger.info(
                    f"[DataMasking] Preparing {len(values_to_mask)} values for field '{field}' with rule {rule_id}"
                )

                # Create batch requests for this field
                for idx, value in enumerate(values_to_mask):
                    request_id = f"field_{field}_{rule_idx}_{idx}"
                    # Use camelCase for Java backend compatibility
                    batch_requests.append({"ruleId": rule_id, "input": value, "requestId": request_id})
                    # Store mapping to DataFrame position
                    row_indices = df[mask].index.tolist()
                    field_mapping.append({"request_id": request_id, "field": field, "row_index": row_indices[idx]})

            if not batch_requests:
                logger.info("[DataMasking] No data to mask")
                return [Data(data=row.to_dict()) for _, row in df.iterrows()]

            logger.info(f"[DataMasking] Processing {len(batch_requests)} total masking requests")

            try:
                # Batch masking using external service with multiple rule IDs
                responses = await client.test_rule_batch_multi(batch_requests)

                # Process responses and update DataFrame
                successful_count = 0
                failed_count = 0

                for response in responses:
                    if not response.get("success", False):
                        # Support both camelCase and snake_case
                        request_id = response.get("requestId") or response.get("request_id")
                        error_msg_text = response.get("errorMessage") or response.get("error_message", "Unknown error")
                        error_msg = f"Masking failed for request {request_id}: {error_msg_text}"
                        logger.error(error_msg)
                        failed_count += 1
                        continue

                    # Find corresponding field and row (support both naming conventions)
                    response_request_id = response.get("requestId") or response.get("request_id")
                    mapping = next((m for m in field_mapping if m["request_id"] == response_request_id), None)
                    if not mapping:
                        logger.warning(f"[DataMasking] No mapping found for request {response_request_id}")
                        continue

                    # Update DataFrame with masked value
                    df.at[mapping["row_index"], mapping["field"]] = response.get("output")
                    successful_count += 1

                logger.info(
                    f"[DataMasking] Successfully masked {successful_count} values, failed {failed_count} values"
                )

                if failed_count > 0:
                    error_msg = f"Masking failed for {failed_count} values"
                    logger.error(error_msg)
                    # Raise error if any failures occurred
                    raise ValueError(error_msg)

            except Exception as e:
                error_msg = f"Batch masking failed: {e!s}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            # Convert back to Data objects
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]

            self.status = i18n.t(
                "components.security.data_masking.status.success",
                count=len(result),
                fields=len(self.masking_rules),
            )

            logger.info(f"[DataMasking] Successfully masked {len(result)} records")
            return result

        except ValueError:
            # Re-raise ValueError directly
            raise
        except Exception as e:
            error_msg = i18n.t("components.security.data_masking.errors.masking_failed", error=str(e))
            logger.exception(f"[DataMasking] {error_msg}")
            self.status = error_msg
            raise ValueError(error_msg) from e

    def get_masking_stats(self) -> Data:
        """Get statistics about the masking operation."""
        try:
            masked_data = self.mask_data()

            stats = {
                "total_records": len(self.data_input) if self.data_input else 0,
                "masked_records": len(masked_data),
                "masking_rules": [
                    {
                        "field": rule.get("field"),
                        "rule_id": rule.get("rule_id"),
                    }
                    for rule in self.masking_rules
                ],
                "total_fields_masked": len(self.masking_rules),
            }

            logger.info(f"[DataMasking] Stats: {stats}")
            return Data(data=stats)

        except Exception as e:
            logger.error(f"[DataMasking] Failed to get masking stats: {e}")
            return Data(
                data={
                    "total_records": 0,
                    "masked_records": 0,
                    "masking_rules": [],
                    "total_fields_masked": 0,
                    "error": str(e),
                }
            )
