from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Operator options with metadata for i18n
OPERATOR_OPTIONS = [
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
                    "formatter": "dropdown",
                    "options": [
                        i18n.t("components.manipulations.field_value_mapping.operators.equal"),
                        i18n.t("components.manipulations.field_value_mapping.operators.not_equal"),
                        i18n.t("components.manipulations.field_value_mapping.operators.greater_than"),
                        i18n.t("components.manipulations.field_value_mapping.operators.less_than"),
                        i18n.t("components.manipulations.field_value_mapping.operators.greater_equal"),
                        i18n.t("components.manipulations.field_value_mapping.operators.less_equal"),
                        i18n.t("components.manipulations.field_value_mapping.operators.contains"),
                        i18n.t("components.manipulations.field_value_mapping.operators.not_contains"),
                        i18n.t("components.manipulations.field_value_mapping.operators.starts_with"),
                        i18n.t("components.manipulations.field_value_mapping.operators.ends_with"),
                        i18n.t("components.manipulations.field_value_mapping.operators.in"),
                        i18n.t("components.manipulations.field_value_mapping.operators.not_in"),
                    ],
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
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.field_value_mapping.outputs.data"),
            method="map_field_values",
        )
    ]

    def update_build_config(
        self, build_config: dict, field_value: Any, field_name: str | None = None, action: str | None = None
    ):
        """Dynamic configuration updates based on action button clicks.

        Args:
            build_config: Current build configuration
            field_value: Value of the field that changed (contains field info from preview API)
            field_name: Name of the field that changed
            action: Name of the action button that was clicked (if any)
        """
        logger.info(f"[FieldValueMapping] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button clicks (from mapping_rules table)
        if field_name == "mapping_rules" and action == "analyze_fields":
            logger.info("[FieldValueMapping] Field analysis triggered by action button")

            try:
                # field_value contains the field info from preview API
                # We need to extract unique field names to populate input_field options

                if not field_value or not isinstance(field_value, list):
                    logger.warning("[FieldValueMapping] Invalid field data received")
                    self.status = i18n.t("components.manipulations.field_value_mapping.errors.no_data_input")
                    return build_config

                # Extract unique field names from the data
                # field_value should be a list of field mappings with source_field
                unique_fields = set()
                for item in field_value:
                    if isinstance(item, dict) and "source_field" in item:
                        unique_fields.add(item["source_field"])

                if not unique_fields:
                    logger.warning("[FieldValueMapping] No fields found in data")
                    self.status = i18n.t("components.manipulations.field_value_mapping.errors.no_fields_found")
                    return build_config

                # Generate empty mapping rules with discovered fields
                # User will fill in operator, compare_value, replacement_value, output_field
                generated_rules = []
                for field_name_str in sorted(unique_fields):
                    generated_rules.append(
                        {
                            "input_field": field_name_str,
                            "operator": "=",  # Default operator
                            "compare_value": "",
                            "replacement_value": "",
                            "output_field": field_name_str,  # Default to same name
                        }
                    )

                # Update mapping_rules with generated data
                build_config["mapping_rules"]["value"] = generated_rules

                logger.info(
                    f"[FieldValueMapping] Field analysis completed, generated {len(generated_rules)} mapping templates"
                )
                self.status = i18n.t(
                    "components.manipulations.field_value_mapping.status.analysis_success", count=len(generated_rules)
                )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[FieldValueMapping] Field analysis failed: {error_msg}")
                self.status = i18n.t(
                    "components.manipulations.field_value_mapping.errors.analysis_failed", error=error_msg
                )
                # Don't throw exception, let user continue to operate

        logger.debug(f"[FieldValueMapping] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _get_operator_value(self, operator_display: str) -> str:
        """Convert display label to operator value using metadata mapping."""
        # Try to find in options_metadata
        for schema in self.inputs:
            if schema.name == "mapping_rules":
                for field in schema.table_schema:
                    if field["name"] == "operator" and "options_metadata" in field:
                        for metadata in field["options_metadata"]:
                            if metadata["label"] == operator_display:
                                return metadata["value"]

        # Fallback: if already a value, return as-is
        if operator_display in OPERATOR_OPTIONS:
            return operator_display

        # Default fallback
        logger.warning(f"Unknown operator display: {operator_display}, using '=' as fallback")
        return "="

    def _evaluate_condition(self, field_value: Any, operator: str, compare_value: str) -> bool:
        """Evaluate whether field value satisfies the condition.

        Args:
            field_value: The field value from data
            operator: Comparison operator (=, !=, >, <, etc.)
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

            logger.warning(f"Unknown operator: {operator_value}")
            return False

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    def map_field_values(self) -> list[Data]:
        """Apply field value mapping rules to multiple fields.

        Returns:
            list[Data]: Transformed data with mapped values

        Raises:
            ValueError: If configuration is invalid or mapping fails
        """
        try:
            # Validate mapping rules exist
            if not self.mapping_rules:
                raise ValueError(i18n.t("components.manipulations.field_value_mapping.errors.missing_config"))

            # Validate each rule has required fields
            for rule in self.mapping_rules:
                if not rule.get("input_field") or not rule.get("output_field"):
                    raise ValueError(i18n.t("components.manipulations.field_value_mapping.errors.missing_fields"))

            # Allow empty data input - just return empty list
            if not self.data_input:
                return []

            self.status = i18n.t("components.manipulations.field_value_mapping.status.processing")

            result_data = []

            # Process each data item
            for data_item in self.data_input:
                # Get original data dictionary
                row_dict = data_item.data if hasattr(data_item, "data") else data_item
                result_dict = row_dict.copy()

                # Track which output fields have been set to avoid overwriting
                # This implements "first match wins" behavior for same output field
                output_fields_set = set()

                # Apply all mapping rules
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

                result_data.append(Data(data=result_dict))

            self.status = i18n.t(
                "components.manipulations.field_value_mapping.status.success",
                count=len(result_data),
                rules=len(self.mapping_rules),
            )

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.manipulations.field_value_mapping.errors.mapping_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
