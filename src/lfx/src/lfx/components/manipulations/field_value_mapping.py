import asyncio
import re
from typing import Any

import i18n

from lfx.base.transformation.script import ScriptTransformation
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Operator options - internal values used for data processing
OPERATOR_VALUES = [
    "=",
    "!=",
    ">",
    "<",
    ">=",
    "<=",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "in",
    "not_in",
    "regex",
]


class ETLFieldValueMappingComponent(Component):
    display_name = i18n.t("components.manipulations.field_value_mapping.display_name")
    description = i18n.t("components.manipulations.field_value_mapping.description")
    icon = "map"
    name = "ETLFieldValueMapping"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.field_value_mapping.data_input.display_name"),
            info=i18n.t("components.manipulations.field_value_mapping.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="mapping_rules",
            display_name=i18n.t("components.manipulations.field_value_mapping.mapping_rules.display_name"),
            info=i18n.t("components.manipulations.field_value_mapping.mapping_rules.info"),
            table_schema=[
                {
                    "name": "input_field",
                    "display_name": i18n.t("components.manipulations.field_value_mapping.input_field"),
                    "type": "str",
                    "required": True,
                    "description": i18n.t("components.manipulations.field_value_mapping.input_field_desc"),
                },
                {
                    "name": "operator",
                    "display_name": i18n.t("components.manipulations.field_value_mapping.operator"),
                    "type": "str",
                    "formatter": "text",
                    "options": OPERATOR_VALUES,
                    "options_metadata": [
                        {"value": "=", "label": i18n.t("components.manipulations.field_value_mapping.operators.equal")},
                        {
                            "value": "!=",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.not_equal"),
                        },
                        {
                            "value": ">",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.greater_than"),
                        },
                        {
                            "value": "<",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.less_than"),
                        },
                        {
                            "value": ">=",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.greater_equal"),
                        },
                        {
                            "value": "<=",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.less_equal"),
                        },
                        {
                            "value": "contains",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.contains"),
                        },
                        {
                            "value": "not_contains",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.not_contains"),
                        },
                        {
                            "value": "starts_with",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.starts_with"),
                        },
                        {
                            "value": "ends_with",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.ends_with"),
                        },
                        {"value": "in", "label": i18n.t("components.manipulations.field_value_mapping.operators.in")},
                        {
                            "value": "not_in",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.not_in"),
                        },
                        {
                            "value": "regex",
                            "label": i18n.t("components.manipulations.field_value_mapping.operators.regex"),
                        },
                    ],
                    "required": True,
                    "description": i18n.t("components.manipulations.field_value_mapping.operator_desc"),
                },
                {
                    "name": "compare_value",
                    "display_name": i18n.t("components.manipulations.field_value_mapping.compare_value"),
                    "type": "str",
                    "required": True,
                    "description": i18n.t("components.manipulations.field_value_mapping.compare_value_desc"),
                },
                {
                    "name": "replacement_value",
                    "display_name": i18n.t("components.manipulations.field_value_mapping.replacement_value"),
                    "type": "str",
                    "required": True,
                    "description": i18n.t("components.manipulations.field_value_mapping.replacement_value_desc"),
                },
                {
                    "name": "output_field",
                    "display_name": i18n.t("components.manipulations.field_value_mapping.output_field"),
                    "type": "str",
                    "required": True,
                    "description": i18n.t("components.manipulations.field_value_mapping.output_field_desc"),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.manipulations.field_value_mapping.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        BoolInput(
            name="enable_script",
            display_name=i18n.t("components.manipulations.field_value_mapping.enable_script.display_name"),
            info=i18n.t("components.manipulations.field_value_mapping.enable_script.info"),
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="script_type",
            display_name=i18n.t("components.manipulations.field_value_mapping.script_type.display_name"),
            info=i18n.t("components.manipulations.field_value_mapping.script_type.info"),
            options=["javascript", "python"],
            value="javascript",
            advanced=True,
        ),
        MultilineInput(
            name="script_content",
            display_name=i18n.t("components.manipulations.field_value_mapping.script_content.display_name"),
            info=i18n.t("components.manipulations.field_value_mapping.script_content.info"),
            placeholder=i18n.t("components.manipulations.field_value_mapping.script_content.placeholder"),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_value_mapping.outputs.data"),
            method="map_field_values",
        )
    ]

    def __init__(self, **kwargs):
        """Initialize component with script transformation support."""
        super().__init__(**kwargs)
        self.script_engine = ScriptTransformation()

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,
        field_name: str | None = None,
        action: str | None = None,
    ):
        """Dynamic configuration updates based on action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (unused in this implementation)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[FieldValueMapping] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button clicks (from mapping_rules table)
        if field_name == "mapping_rules" and action == "analyze_fields":
            logger.info("[FieldValueMapping] Field analysis triggered by action button")

            try:
                # Try to get graph_data and node_id from build_config first (passed from frontend)
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # If not in build_config, try to get from self.graph (runtime context)
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        # PlaceholderGraph - no data available
                        logger.warning("[FieldValueMapping] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[FieldValueMapping] No graph data available")
                    self.status = i18n.t("components.manipulations.field_value_mapping.errors.no_graph_data")
                    return build_config

                mapping_rules = []

                # Primary strategy: Try to execute upstream node to get actual data
                # Enhanced with retry mechanism for "has not been built yet" errors
                max_retries = 2
                upstream_data = None

                for attempt in range(max_retries):
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        if upstream_data:
                            # Extract field names and sample values from upstream data
                            mapping_rules = self._extract_mapping_rules_with_samples(upstream_data)
                            logger.info(
                                f"[FieldValueMapping] Extracted {len(mapping_rules)} mapping rules from upstream data (attempt {attempt + 1})"
                            )
                            break
                        logger.warning(
                            f"[FieldValueMapping] No data returned from upstream node (attempt {attempt + 1})"
                        )

                    except ValueError as e:
                        error_msg = str(e)
                        if "has not been built yet" in error_msg and attempt < max_retries - 1:
                            logger.warning(
                                f"[FieldValueMapping] Upstream node not built, retrying... (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(0.2)  # Brief delay before retry
                            continue
                        # Fallback strategy: Extract from upstream node configuration
                        logger.warning(
                            f"[FieldValueMapping] Upstream execution failed after {attempt + 1} attempts: {e}. Trying static analysis..."
                        )
                        break
                    except Exception as e:
                        logger.warning(
                            f"[FieldValueMapping] Unexpected error during upstream execution: {e}. Falling back to static analysis..."
                        )
                        break

                # If we couldn't get data from execution, try static analysis
                if not upstream_data:
                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        field_names = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "FieldValueMapping"
                        )

                        if field_names:
                            # Generate mapping rules from field names (without sample values)
                            mapping_rules = [
                                {
                                    "input_field": field_name,
                                    "operator": "=",  # Default operator
                                    "compare_value": "",
                                    "replacement_value": "",
                                    "output_field": field_name,  # Default: same as input
                                }
                                for field_name in field_names
                            ]
                            logger.info(
                                f"[FieldValueMapping] Extracted {len(mapping_rules)} mapping rules from static config"
                            )
                        else:
                            logger.warning("[FieldValueMapping] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[FieldValueMapping] Static analysis also failed")

                # Update build_config with results
                if mapping_rules:
                    build_config["mapping_rules"]["value"] = mapping_rules
                    self.status = i18n.t(
                        "components.manipulations.field_value_mapping.status.analysis_success", count=len(mapping_rules)
                    )
                else:
                    self.status = i18n.t("components.manipulations.field_value_mapping.warnings.field_load_failed")
                    logger.warning("[FieldValueMapping] No fields extracted from upstream data")

            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[FieldValueMapping] Field analysis failed with unexpected error")
                self.status = i18n.t("components.manipulations.field_value_mapping.errors.graph_not_available")

        # Show/hide script fields based on enable_script
        if field_name == "enable_script":
            if field_value:
                build_config["script_type"]["advanced"] = False
                build_config["script_content"]["advanced"] = False
            else:
                build_config["script_type"]["advanced"] = True
                build_config["script_content"]["advanced"] = True

        logger.debug(f"[FieldValueMapping] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_mapping_rules_with_samples(self, data_list: list[Data]) -> list[dict]:
        """Extract mapping rules from upstream data with sample values.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of mapping rule dictionaries with sample values for reference
        """
        try:
            if not data_list:
                return []

            # Get first few records to extract field names and sample values
            sample_size = min(3, len(data_list))
            sample_records = data_list[:sample_size]

            # Extract field names from first record
            first_record = sample_records[0]
            if hasattr(first_record, "data"):
                data_dict = first_record.data
            elif isinstance(first_record, dict):
                data_dict = first_record
            else:
                logger.warning(f"[FieldValueMapping] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[FieldValueMapping] Expected dict, got {type(data_dict)}")
                return []

            # Generate mapping rules with sample values
            mapping_rules = []
            for field_name in data_dict:
                # Collect sample values from multiple records
                sample_values = []
                for record in sample_records:
                    if hasattr(record, "data"):
                        value = record.data.get(field_name)
                    else:
                        value = record.get(field_name) if isinstance(record, dict) else None
                    if value is not None and value not in sample_values:
                        sample_values.append(str(value))

                # Create a comment with sample values for user reference
                sample_comment = f"Samples: {', '.join(sample_values[:3])}" if sample_values else ""

                mapping_rules.append(
                    {
                        "input_field": field_name,
                        "operator": "=",  # Default operator
                        "compare_value": sample_values[0] if sample_values else "",  # Pre-fill with first sample
                        "replacement_value": "",
                        "output_field": field_name,  # Default: same as input
                    }
                )

            logger.debug(f"[FieldValueMapping] Extracted {len(mapping_rules)} mapping rules with samples")
            return mapping_rules

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[FieldValueMapping] Failed to extract mapping rules")
            return []

    def _get_operator_value(self, operator_input: Any) -> str:
        """Convert operator input to operator value."""
        # OPERATOR_VALUES contains simple strings, so just validate and return
        if isinstance(operator_input, str):
            # Check if it's a valid operator
            if operator_input in OPERATOR_VALUES:
                return operator_input

        # Default fallback
        logger.warning(f"Unknown operator input: {operator_input}, using '=' as fallback")
        return "="

    def _evaluate_condition(self, field_value: Any, operator: str, compare_value: str) -> bool:
        """Evaluate whether field value satisfies the condition.

        Args:
            field_value: The field value from data
            operator: Comparison operator (=, !=, >, <, regex, etc.)
            compare_value: Value to compare against

        Returns:
            bool: True if condition is satisfied
        """
        try:
            # Convert to string for comparison
            field_str = str(field_value) if field_value is not None else ""
            compare_str = str(compare_value)

            # Convert operator display to value if needed
            operator_value = self._get_operator_value(operator)

            # Basic comparison operators
            if operator_value == "=":
                return field_str == compare_str
            if operator_value == "!=":
                return field_str != compare_str
            if operator_value == ">":
                try:
                    return float(field_str) > float(compare_str)
                except ValueError:
                    return field_str > compare_str
            if operator_value == "<":
                try:
                    return float(field_str) < float(compare_str)
                except ValueError:
                    return field_str < compare_str
            if operator_value == ">=":
                try:
                    return float(field_str) >= float(compare_str)
                except ValueError:
                    return field_str >= compare_str
            if operator_value == "<=":
                try:
                    return float(field_str) <= float(compare_str)
                except ValueError:
                    return field_str <= compare_str

            # String operators
            if operator_value == "contains":
                return compare_str in field_str
            if operator_value == "not_contains":
                return compare_str not in field_str
            if operator_value == "starts_with":
                return field_str.startswith(compare_str)
            if operator_value == "ends_with":
                return field_str.endswith(compare_str)

            # Set operators
            if operator_value == "in":
                compare_list = [v.strip() for v in compare_str.split(",")]
                return field_str in compare_list
            if operator_value == "not_in":
                compare_list = [v.strip() for v in compare_str.split(",")]
                return field_str not in compare_list

            # Regular expression operator
            if operator_value == "regex":
                try:
                    pattern = re.compile(compare_str)
                    return bool(pattern.match(field_str))
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{compare_str}': {e}")
                    return False

            logger.warning(f"Unknown operator: {operator_value}")
            return False

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    def _apply_script_mapping(self, row_dict: dict) -> dict:
        """Apply script-based mapping to a row of data.

        Args:
            row_dict: The row data dictionary

        Returns:
            Modified row dictionary after script execution
        """
        if not self.enable_script or not self.script_content:
            return row_dict

        try:
            # Make a copy to avoid modifying original
            result_dict = row_dict.copy()

            if self.script_type == "javascript":
                # Execute JavaScript with full row context
                # The script can access 'row' object and modify it
                # Example script:
                # if (row.gender == '1') row.gender_text = 'Male';
                # if (row.age > 65) row.category = 'Senior';
                script_result = self.script_engine.execute_javascript(
                    value=result_dict, script=self.script_content, row_data=result_dict
                )
                if isinstance(script_result, dict):
                    result_dict = script_result

            elif self.script_type == "python":
                # Execute Python script with full row context
                # The script can access 'row' dict and modify 'result'
                # Example script:
                # if row.get('gender') == '1':
                #     result['gender_text'] = 'Male'
                # if row.get('age', 0) > 65:
                #     result['category'] = 'Senior'
                script_result = self.script_engine.execute_python(
                    value=result_dict, script=self.script_content, row_data=result_dict
                )
                if isinstance(script_result, dict):
                    result_dict = script_result

            return result_dict

        except Exception as e:
            logger.error(f"Script execution error: {e}")
            # Return original data on error
            return row_dict

    def map_field_values(self) -> list[Data]:
        """Apply field value mapping rules to multiple fields with optional script support.

        Returns:
            list[Data]: Transformed data with mapped values

        Raises:
            ValueError: If configuration is invalid or mapping fails
        """
        try:
            # Allow script-only mode (no mapping rules required if script is enabled)
            if not self.mapping_rules and not self.enable_script:
                raise ValueError(i18n.t("components.manipulations.field_value_mapping.errors.missing_config"))

            # Validate each rule has required fields (if rules exist)
            if self.mapping_rules:
                for rule in self.mapping_rules:
                    if not rule.get("input_field") or not rule.get("output_field"):
                        raise ValueError(i18n.t("components.manipulations.field_value_mapping.errors.missing_fields"))

            # Allow empty data input - just return empty list
            if not self.data_input:
                return []

            self.status = i18n.t("components.manipulations.field_value_mapping.status.processing")

            result_data = []

            # Handle both single Data objects and lists of Data objects
            data_items = self.data_input
            if not isinstance(data_items, list):
                data_items = [data_items]

            # Process each data item
            for data_item in data_items:
                # Get original data dictionary with proper error handling
                if hasattr(data_item, "data") and isinstance(data_item.data, dict):
                    row_dict = data_item.data
                elif isinstance(data_item, dict):
                    row_dict = data_item
                elif isinstance(data_item, tuple):
                    # Handle tuple case - try to extract meaningful data
                    logger.warning(f"Received tuple instead of Data object: {data_item}")
                    if len(data_item) >= 2 and isinstance(data_item[1], dict):
                        row_dict = data_item[1]  # Use the second element if it's a dict
                    else:
                        logger.error(f"Cannot process tuple: {data_item}")
                        continue
                else:
                    logger.warning(f"Unknown data type {type(data_item)}: {data_item}")
                    continue

                result_dict = row_dict.copy()

                # Track which output fields have been set to avoid overwriting
                # This implements "first match wins" behavior for same output field
                output_fields_set = set()

                # Apply all mapping rules
                if self.mapping_rules:
                    for rule in self.mapping_rules:
                        input_field = rule.get("input_field")
                        operator = rule.get("operator", "=")
                        compare_value = rule.get("compare_value", "")
                        replacement_value = rule.get("replacement_value", "")
                        output_field = rule.get("output_field")

                        # Check if input field exists
                        if input_field not in row_dict:
                            logger.debug(
                                i18n.t(
                                    "components.manipulations.field_value_mapping.warnings.field_not_found",
                                    field=input_field,
                                )
                            )
                            continue

                        field_value = row_dict[input_field]

                        # Skip if output field already mapped (first match wins)
                        if output_field in output_fields_set:
                            continue

                        # Evaluate condition
                        if self._evaluate_condition(field_value, operator, compare_value):
                            # Condition satisfied, write replacement value to output field
                            result_dict[output_field] = replacement_value
                            output_fields_set.add(output_field)
                            logger.debug(f"Mapped {input_field}={field_value} -> {output_field}={replacement_value}")

                # Apply script-based mapping if enabled
                if self.enable_script:
                    result_dict = self._apply_script_mapping(result_dict)

                result_data.append(Data(data=result_dict))

            # Build success message
            success_parts = []
            if self.mapping_rules:
                success_parts.append(f"{len(self.mapping_rules)} rules")
            if self.enable_script:
                success_parts.append(f"{self.script_type} script")

            self.status = i18n.t(
                "components.manipulations.field_value_mapping.status.success",
                count=len(result_data),
                rules=", ".join(success_parts) if success_parts else "0 rules",
            )

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_value_mapping.errors.mapping_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
