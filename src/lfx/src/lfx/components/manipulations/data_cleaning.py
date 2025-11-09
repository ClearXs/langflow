import re
from typing import Any

import i18n

from lfx.base.transformation import TransformationExecutor
from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, IntInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema import Data

# Operator options for filter conditions (internal values)
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

# Transformation rule options - based on ETLCloud documentation (internal values)
TRANSFORMATION_RULE_VALUES = [
    "none",
    "to_number",
    "trim",
    "trim_all",
    "substring_after",
    "substring_before",
    "replace_string",
    "timestamp_to_string",
    "upper",
    "lower",
    "amount_to_chinese",
    "substring",
    "date_format",
    "mask_phone",
    "mask_idcard",
    "mask_email",
    "mask_name",
    "md5",
    "sha256",
    "to_int",
    "to_float",
    "to_str",
    "to_bool",
    "expression",
    "javascript",
    "python",
]


# Helper function to generate value-to-label mapping
def get_operator_value_to_label():
    """Get operator value to i18n label mapping."""
    return {
        "=": i18n.t("components.manipulations.data_cleaning.operators.equal"),
        "!=": i18n.t("components.manipulations.data_cleaning.operators.not_equal"),
        ">": i18n.t("components.manipulations.data_cleaning.operators.greater_than"),
        "<": i18n.t("components.manipulations.data_cleaning.operators.less_than"),
        ">=": i18n.t("components.manipulations.data_cleaning.operators.greater_equal"),
        "<=": i18n.t("components.manipulations.data_cleaning.operators.less_equal"),
        "contains": i18n.t("components.manipulations.data_cleaning.operators.contains"),
        "not_contains": i18n.t("components.manipulations.data_cleaning.operators.not_contains"),
        "starts_with": i18n.t("components.manipulations.data_cleaning.operators.starts_with"),
        "ends_with": i18n.t("components.manipulations.data_cleaning.operators.ends_with"),
        "in": i18n.t("components.manipulations.data_cleaning.operators.in"),
        "not_in": i18n.t("components.manipulations.data_cleaning.operators.not_in"),
        "regex": i18n.t("components.manipulations.data_cleaning.operators.regex"),
    }


def get_transformation_rule_value_to_label():
    """Get transformation rule value to i18n label mapping."""
    return {
        "none": i18n.t("components.manipulations.data_cleaning.transformation_rules.none"),
        "to_number": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_number"),
        "trim": i18n.t("components.manipulations.data_cleaning.transformation_rules.trim"),
        "trim_all": i18n.t("components.manipulations.data_cleaning.transformation_rules.trim_all"),
        "substring_after": i18n.t("components.manipulations.data_cleaning.transformation_rules.substring_after"),
        "substring_before": i18n.t("components.manipulations.data_cleaning.transformation_rules.substring_before"),
        "replace_string": i18n.t("components.manipulations.data_cleaning.transformation_rules.replace_string"),
        "timestamp_to_string": i18n.t(
            "components.manipulations.data_cleaning.transformation_rules.timestamp_to_string"
        ),
        "upper": i18n.t("components.manipulations.data_cleaning.transformation_rules.upper"),
        "lower": i18n.t("components.manipulations.data_cleaning.transformation_rules.lower"),
        "amount_to_chinese": i18n.t("components.manipulations.data_cleaning.transformation_rules.amount_to_chinese"),
        "substring": i18n.t("components.manipulations.data_cleaning.transformation_rules.substring"),
        "date_format": i18n.t("components.manipulations.data_cleaning.transformation_rules.date_format"),
        "mask_phone": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_phone"),
        "mask_idcard": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_idcard"),
        "mask_email": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_email"),
        "mask_name": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_name"),
        "md5": i18n.t("components.manipulations.data_cleaning.transformation_rules.md5"),
        "sha256": i18n.t("components.manipulations.data_cleaning.transformation_rules.sha256"),
        "to_int": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_int"),
        "to_float": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_float"),
        "to_str": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_str"),
        "to_bool": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_bool"),
        "expression": i18n.t("components.manipulations.data_cleaning.transformation_rules.expression"),
        "javascript": i18n.t("components.manipulations.data_cleaning.transformation_rules.javascript"),
        "python": i18n.t("components.manipulations.data_cleaning.transformation_rules.python"),
    }


def get_logic_operator_value_to_label():
    """Get logic operator value to i18n label mapping."""
    return {
        "AND": i18n.t("components.manipulations.data_cleaning.logic_operators.and"),
        "OR": i18n.t("components.manipulations.data_cleaning.logic_operators.or"),
    }


class ETLDataCleaningComponent(Component):
    display_name = i18n.t("components.manipulations.data_cleaning.display_name")
    description = i18n.t("components.manipulations.data_cleaning.description")
    icon = "eraser"
    name = "ETLDataCleaning"

    def __init__(self, **kwargs):
        """Initialize component with transformation executor."""
        super().__init__(**kwargs)
        self.transformation_executor = TransformationExecutor()

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.manipulations.data_cleaning.data_input.display_name"),
            info=i18n.t("components.manipulations.data_cleaning.data_input.info"),
            is_list=True,
            required=True,
        ),
        TableInput(
            name="filter_conditions",
            display_name=i18n.t("components.manipulations.data_cleaning.filter_conditions.display_name"),
            info=i18n.t("components.manipulations.data_cleaning.filter_conditions.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.manipulations.data_cleaning.filter_conditions.field_name"),
                    "type": "str",
                    "description": i18n.t("components.manipulations.data_cleaning.filter_conditions.field_name_desc"),
                },
                {
                    "name": "operator",
                    "display_name": i18n.t("components.manipulations.data_cleaning.filter_conditions.operator"),
                    "type": "str",
                    "formatter": "text",
                    "options": OPERATOR_VALUES,
                    "options_metadata": [
                        {"value": "=", "label": i18n.t("components.manipulations.data_cleaning.operators.equal")},
                        {"value": "!=", "label": i18n.t("components.manipulations.data_cleaning.operators.not_equal")},
                        {
                            "value": ">",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.greater_than"),
                        },
                        {"value": "<", "label": i18n.t("components.manipulations.data_cleaning.operators.less_than")},
                        {
                            "value": ">=",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.greater_equal"),
                        },
                        {"value": "<=", "label": i18n.t("components.manipulations.data_cleaning.operators.less_equal")},
                        {
                            "value": "contains",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.contains"),
                        },
                        {
                            "value": "not_contains",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.not_contains"),
                        },
                        {
                            "value": "starts_with",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.starts_with"),
                        },
                        {
                            "value": "ends_with",
                            "label": i18n.t("components.manipulations.data_cleaning.operators.ends_with"),
                        },
                        {"value": "in", "label": i18n.t("components.manipulations.data_cleaning.operators.in")},
                        {"value": "not_in", "label": i18n.t("components.manipulations.data_cleaning.operators.not_in")},
                        {"value": "regex", "label": i18n.t("components.manipulations.data_cleaning.operators.regex")},
                    ],
                    "description": i18n.t("components.manipulations.data_cleaning.filter_conditions.operator_desc"),
                },
                {
                    "name": "compare_value",
                    "display_name": i18n.t("components.manipulations.data_cleaning.filter_conditions.compare_value"),
                    "type": "str",
                    "description": i18n.t(
                        "components.manipulations.data_cleaning.filter_conditions.compare_value_desc"
                    ),
                },
                {
                    "name": "logic_operator",
                    "display_name": i18n.t("components.manipulations.data_cleaning.filter_conditions.logic_operator"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["AND", "OR"],
                    "options_metadata": [
                        {"value": "AND", "label": i18n.t("components.manipulations.data_cleaning.logic_operators.and")},
                        {"value": "OR", "label": i18n.t("components.manipulations.data_cleaning.logic_operators.or")},
                    ],
                    "description": i18n.t(
                        "components.manipulations.data_cleaning.filter_conditions.logic_operator_desc"
                    ),
                },
            ],
            value=[],
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_filter_fields",
                        "label": i18n.t("components.manipulations.data_cleaning.filter_conditions.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
            advanced=False,  # Make it visible by default
        ),
        TableInput(
            name="cleaning_rules",
            display_name=i18n.t("components.manipulations.data_cleaning.cleaning_rules.display_name"),
            info=i18n.t("components.manipulations.data_cleaning.cleaning_rules.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.manipulations.data_cleaning.cleaning_rules.field_name"),
                    "type": "str",
                    "required": True,
                    "description": i18n.t("components.manipulations.data_cleaning.cleaning_rules.field_name_desc"),
                },
                {
                    "name": "transformation_rule",
                    "display_name": i18n.t("components.manipulations.data_cleaning.cleaning_rules.transformation_rule"),
                    "type": "str",
                    "formatter": "text",
                    "options": TRANSFORMATION_RULE_VALUES,
                    "options_metadata": [
                        {
                            "value": "none",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.none"),
                        },
                        {
                            "value": "to_number",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_number"),
                        },
                        {
                            "value": "trim",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.trim"),
                        },
                        {
                            "value": "trim_all",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.trim_all"),
                        },
                        {
                            "value": "substring_after",
                            "label": i18n.t(
                                "components.manipulations.data_cleaning.transformation_rules.substring_after"
                            ),
                        },
                        {
                            "value": "substring_before",
                            "label": i18n.t(
                                "components.manipulations.data_cleaning.transformation_rules.substring_before"
                            ),
                        },
                        {
                            "value": "replace_string",
                            "label": i18n.t(
                                "components.manipulations.data_cleaning.transformation_rules.replace_string"
                            ),
                        },
                        {
                            "value": "timestamp_to_string",
                            "label": i18n.t(
                                "components.manipulations.data_cleaning.transformation_rules.timestamp_to_string"
                            ),
                        },
                        {
                            "value": "upper",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.upper"),
                        },
                        {
                            "value": "lower",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.lower"),
                        },
                        {
                            "value": "amount_to_chinese",
                            "label": i18n.t(
                                "components.manipulations.data_cleaning.transformation_rules.amount_to_chinese"
                            ),
                        },
                        {
                            "value": "substring",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.substring"),
                        },
                        {
                            "value": "date_format",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.date_format"),
                        },
                        {
                            "value": "mask_phone",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_phone"),
                        },
                        {
                            "value": "mask_idcard",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_idcard"),
                        },
                        {
                            "value": "mask_email",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_email"),
                        },
                        {
                            "value": "mask_name",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.mask_name"),
                        },
                        {
                            "value": "md5",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.md5"),
                        },
                        {
                            "value": "sha256",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.sha256"),
                        },
                        {
                            "value": "to_int",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_int"),
                        },
                        {
                            "value": "to_float",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_float"),
                        },
                        {
                            "value": "to_str",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_str"),
                        },
                        {
                            "value": "to_bool",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.to_bool"),
                        },
                        {
                            "value": "expression",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.expression"),
                        },
                        {
                            "value": "javascript",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.javascript"),
                        },
                        {
                            "value": "python",
                            "label": i18n.t("components.manipulations.data_cleaning.transformation_rules.python"),
                        },
                    ],
                    "description": i18n.t(
                        "components.manipulations.data_cleaning.cleaning_rules.transformation_rule_desc"
                    ),
                },
                {
                    "name": "custom_expression",
                    "display_name": i18n.t("components.manipulations.data_cleaning.cleaning_rules.custom_expression"),
                    "type": "str",
                    "description": i18n.t(
                        "components.manipulations.data_cleaning.cleaning_rules.custom_expression_desc"
                    ),
                },
            ],
            value=[],
            required=True,
            table_options={
                "action_buttons": [
                    {
                        "name": "analyze_fields",
                        "label": i18n.t("components.manipulations.data_cleaning.cleaning_rules.analyze_button"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ],
            },
        ),
        IntInput(
            name="max_records",
            display_name=i18n.t("components.manipulations.data_cleaning.max_records.display_name"),
            info=i18n.t("components.manipulations.data_cleaning.max_records.info"),
            value=0,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.manipulations.data_cleaning.outputs.data.display_name"),
            method="clean_data",
        )
    ]

    async def update_build_config(
        self,
        build_config: dict,
        field_value: Any,  # noqa: ARG002
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
        logger.info(f"[DataCleaning] update_build_config called - field_name: {field_name}, action: {action}")

        # Handle action button for filter conditions field analysis
        if field_name == "filter_conditions" and action == "analyze_filter_fields":
            logger.info("[DataCleaning] Filter field analysis triggered by action button")

            try:
                # Get graph_data and node_id
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning("[DataCleaning] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[DataCleaning] No graph data available for filter conditions")
                    self.status = i18n.t("components.manipulations.data_cleaning.errors.no_graph_data")
                    return build_config

                filter_fields = []

                # Primary strategy: Try to execute upstream node to get actual data
                try:
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                    )

                    if upstream_data:
                        # Extract field names for filter conditions
                        filter_fields = self._extract_filter_fields(upstream_data)
                        logger.info(f"[DataCleaning] Extracted {len(filter_fields)} filter fields from upstream data")
                    else:
                        logger.warning("[DataCleaning] No data returned from upstream node for filter conditions")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configuration
                    logger.warning(f"[DataCleaning] Upstream execution failed: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        fields = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "DataCleaning"
                        )

                        if fields:
                            # Generate filter conditions from field names
                            filter_fields = [
                                {
                                    "field_name": field["name"],
                                    "operator": "=",  # Default operator
                                    "compare_value": "",
                                    "logic_operator": "AND",  # Default logic
                                }
                                for field in fields
                            ]
                            logger.info(
                                f"[DataCleaning] Extracted {len(filter_fields)} filter fields from static config"
                            )
                        else:
                            logger.warning("[DataCleaning] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[DataCleaning] Static analysis also failed")

                # Update build_config with results
                if filter_fields:
                    build_config["filter_conditions"]["value"] = filter_fields
                    self.status = i18n.t(
                        "components.manipulations.data_cleaning.status.filter_analysis_success",
                        count=len(filter_fields),
                    )
                else:
                    self.status = i18n.t("components.manipulations.data_cleaning.warnings.field_load_failed")
                    logger.warning("[DataCleaning] No fields extracted for filter conditions")

            except Exception:  # noqa: BLE001
                logger.exception("[DataCleaning] Filter field analysis failed with unexpected error")
                self.status = i18n.t("components.manipulations.data_cleaning.errors.graph_not_available")

        # Handle action button clicks (from cleaning_rules table)
        if field_name == "cleaning_rules" and action == "analyze_fields":
            logger.info("[DataCleaning] Field analysis triggered by action button")

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
                        logger.warning("[DataCleaning] PlaceholderGraph detected - no graph data available")

                if not graph_data:
                    logger.warning("[DataCleaning] No graph data available")
                    self.status = i18n.t("components.manipulations.data_cleaning.errors.no_graph_data")
                    return build_config

                cleaning_rules = []

                # Primary strategy: Try to execute upstream node to get actual data
                try:
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                    )

                    if upstream_data:
                        # Extract field names and generate cleaning rules
                        cleaning_rules = self._extract_cleaning_rules(upstream_data)
                        logger.info(f"[DataCleaning] Extracted {len(cleaning_rules)} cleaning rules from upstream data")
                    else:
                        logger.warning("[DataCleaning] No data returned from upstream node")

                except ValueError as e:
                    # Fallback strategy: Extract from upstream node configuration
                    logger.warning(f"[DataCleaning] Upstream execution failed: {e}. Trying static analysis...")

                    try:
                        from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                        fields = find_and_extract_upstream_fields(
                            graph_data, node_id, "data_input", "DataCleaning"
                        )

                        if fields:
                            # Generate cleaning rules from field names
                            cleaning_rules = [
                                {
                                    "field_name": field["name"],
                                    "transformation_rule": "none",  # Default: no transformation
                                    "custom_expression": "",
                                }
                                for field in fields
                            ]
                            logger.info(
                                f"[DataCleaning] Extracted {len(cleaning_rules)} cleaning rules from static config"
                            )
                        else:
                            logger.warning("[DataCleaning] Static analysis returned no fields")

                    except Exception:  # noqa: BLE001
                        logger.exception("[DataCleaning] Static analysis also failed")

                # Update build_config with results
                if cleaning_rules:
                    build_config["cleaning_rules"]["value"] = cleaning_rules
                    self.status = i18n.t(
                        "components.manipulations.data_cleaning.status.analysis_success", count=len(cleaning_rules)
                    )
                else:
                    self.status = i18n.t("components.manipulations.data_cleaning.warnings.field_load_failed")
                    logger.warning("[DataCleaning] No fields extracted from upstream data")

            except Exception:  # noqa: BLE001
                # Handle unexpected errors - broad exception needed for production stability
                logger.exception("[DataCleaning] Field analysis failed with unexpected error")
                self.status = i18n.t("components.manipulations.data_cleaning.errors.graph_not_available")

        logger.debug(f"[DataCleaning] Returning build_config with keys: {list(build_config.keys())}")
        return build_config

    def _extract_filter_fields(self, data_list: list[Data]) -> list[dict]:
        """Extract filter field conditions from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of filter condition dictionaries
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
                logger.warning(f"[DataCleaning] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[DataCleaning] Expected dict, got {type(data_dict)}")
                return []

            # Generate filter conditions for each field
            filter_fields = []
            for field_name in data_dict:
                filter_fields.append(
                    {
                        "field_name": field_name,
                        "operator": "=",  # Default operator
                        "compare_value": "",
                        "logic_operator": "AND",  # Default logic
                    }
                )

            logger.debug(f"[DataCleaning] Extracted {len(filter_fields)} filter fields")
            return filter_fields

        except Exception:  # noqa: BLE001
            logger.exception("[DataCleaning] Failed to extract filter fields")
            return []

    def _extract_cleaning_rules(self, data_list: list[Data]) -> list[dict]:
        """Extract cleaning rules from upstream data.

        Args:
            data_list: List of Data objects from upstream node

        Returns:
            List of cleaning rule dictionaries with field names
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
                logger.warning(f"[DataCleaning] Unexpected data type: {type(first_record)}")
                return []

            if not isinstance(data_dict, dict):
                logger.warning(f"[DataCleaning] Expected dict, got {type(data_dict)}")
                return []

            # Generate cleaning rules for each field
            cleaning_rules = []
            for field_name in data_dict:
                cleaning_rules.append(
                    {
                        "field_name": field_name,
                        "transformation_rule": "none",  # Default: no transformation
                        "custom_expression": "",
                    }
                )

            logger.debug(f"[DataCleaning] Extracted {len(cleaning_rules)} cleaning rules")
            return cleaning_rules

        except Exception:  # noqa: BLE001
            # Broad exception needed to handle various data format issues
            logger.exception("[DataCleaning] Failed to extract cleaning rules")
            return []

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

            # Basic comparison operators
            if operator == "=":
                return field_str == compare_str
            if operator == "!=":
                return field_str != compare_str
            if operator == ">":
                try:
                    return float(field_str) > float(compare_str)
                except ValueError:
                    return field_str > compare_str
            if operator == "<":
                try:
                    return float(field_str) < float(compare_str)
                except ValueError:
                    return field_str < compare_str
            if operator == ">=":
                try:
                    return float(field_str) >= float(compare_str)
                except ValueError:
                    return field_str >= compare_str
            if operator == "<=":
                try:
                    return float(field_str) <= float(compare_str)
                except ValueError:
                    return field_str <= compare_str

            # String operators
            if operator == "contains":
                return compare_str in field_str
            if operator == "not_contains":
                return compare_str not in field_str
            if operator == "starts_with":
                return field_str.startswith(compare_str)
            if operator == "ends_with":
                return field_str.endswith(compare_str)

            # Set operators
            if operator == "in":
                compare_list = [v.strip() for v in compare_str.split(",")]
                return field_str in compare_list
            if operator == "not_in":
                compare_list = [v.strip() for v in compare_str.split(",")]
                return field_str not in compare_list

            # Regular expression operator
            if operator == "regex":
                try:
                    pattern = re.compile(compare_str)
                    return bool(pattern.match(field_str))
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{compare_str}': {e}")
                    return False

            logger.warning(f"Unknown operator: {operator}")
            return False

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    def _evaluate_filter_conditions(self, row_dict: dict) -> bool:
        """Evaluate whether record satisfies filter conditions.

        Args:
            row_dict: The row data dictionary

        Returns:
            bool: True if record passes filter conditions
        """
        if not self.filter_conditions:
            return True  # No filter conditions, all records pass

        # Evaluate all conditions
        results = []
        for condition in self.filter_conditions:
            field_name = condition.get("field_name")
            operator = condition.get("operator", "=")
            compare_value = condition.get("compare_value", "")
            logic_operator = condition.get("logic_operator", "AND")

            # Get field value
            field_value = row_dict.get(field_name)

            # Evaluate condition
            result = self._evaluate_condition(field_value, operator, compare_value)
            results.append((result, logic_operator))

        # Compute final result based on logic operators
        if not results:
            return True

        # Start with first result
        final_result = results[0][0]

        # Apply logic operators sequentially
        for i in range(1, len(results)):
            prev_logic = results[i - 1][1]  # Logic operator from previous condition
            current_result = results[i][0]

            if prev_logic == "AND":
                final_result = final_result and current_result
            elif prev_logic == "OR":
                final_result = final_result or current_result

        return final_result

    def _apply_cleaning_rules(self, row_dict: dict) -> dict:
        """Apply cleaning rules to a single row of data.

        Args:
            row_dict: The row data dictionary

        Returns:
            Cleaned row dictionary
        """
        result = row_dict.copy()

        for rule in self.cleaning_rules:
            field_name = rule.get("field_name")
            transformation_rule = rule.get("transformation_rule", "none")
            custom_expression = rule.get("custom_expression", "")

            if not field_name or field_name not in result:
                continue

            value = result[field_name]

            # Skip if no transformation
            if transformation_rule == "none":
                continue

            try:
                # Build rule for transformation executor
                if transformation_rule in ["expression", "javascript", "python"]:
                    # Script-based transformations require custom_expression
                    if not custom_expression:
                        logger.warning(
                            f"Skipping {transformation_rule} for {field_name}: no custom_expression provided"
                        )
                        continue
                    rule_config = {"type": transformation_rule, "content": custom_expression}
                elif custom_expression:
                    # Built-in transformation with custom parameters (for functions that need args)
                    # Try to parse custom_expression as parameters
                    rule_config = self._build_builtin_rule_with_params(transformation_rule, custom_expression)
                else:
                    # Simple built-in transformation (no parameters needed)
                    rule_config = transformation_rule

                # Apply transformation
                transformed_value = self.transformation_executor.apply_transformation(value, rule_config, row_dict)
                result[field_name] = transformed_value
                logger.debug(f"Applied {transformation_rule} to {field_name}: {value} -> {transformed_value}")

            except Exception as e:
                logger.error(f"Error applying transformation to {field_name}: {e}")
                # Keep original value on error
                continue

        return result

    def _build_builtin_rule_with_params(self, transformation_rule: str, custom_expression: str) -> str | dict:
        """Build rule configuration for built-in transformations that require parameters.

        Args:
            transformation_rule: The transformation rule name
            custom_expression: Custom parameters as string (comma-separated or JSON-like)

        Returns:
            Rule configuration (string or dict)
        """
        # For built-in transformations that don't need parameters, just return the rule name
        no_param_rules = [
            "none",
            "to_number",
            "trim",
            "trim_all",
            "upper",
            "lower",
            "amount_to_chinese",
            "mask_phone",
            "mask_idcard",
            "mask_email",
            "mask_name",
            "md5",
            "sha256",
            "to_int",
            "to_float",
            "to_str",
            "to_bool",
        ]

        if transformation_rule in no_param_rules:
            return transformation_rule

        # For transformations that need parameters, we need to handle them specially
        # Since the builtin transformation methods don't support parameter passing,
        # we'll convert these to expression-based transformations

        param_based_rules = {
            "substring_after": lambda val, sep: f'{val}.split("{sep}", 1)[1] if "{sep}" in {val} else {val}',
            "substring_before": lambda val, sep: f'{val}.split("{sep}", 1)[0] if "{sep}" in {val} else {val}',
            "replace_string": lambda val, old, new: f'{val}.replace("{old}", "{new}")',
            "substring": lambda val, start, length="": (
                f"{val}[{start}:{start}+{length}]" if length else f"{val}[{start}:]"
            ),
            "timestamp_to_string": lambda val, fmt: f'datetime.fromtimestamp({val}).strftime("{fmt}")',
            "date_format": lambda val, in_fmt, out_fmt: f'datetime.strptime({val}, "{in_fmt}").strftime("{out_fmt}")',
        }

        # If this rule needs parameters but none provided, use the simple rule
        if transformation_rule in param_based_rules and not custom_expression:
            logger.warning(
                f"Transformation {transformation_rule} typically requires parameters, but none provided. Using defaults."
            )
            return transformation_rule

        # For now, if custom_expression is provided for a built-in rule,
        # treat it as an expression that should be evaluated
        # The custom_expression should contain the full logic
        if custom_expression:
            return {"type": "expression", "content": custom_expression}

        return transformation_rule

    def clean_data(self) -> list[Data]:
        """Execute data cleaning with filter conditions and transformation rules.

        Returns:
            list[Data]: Cleaned data

        Raises:
            ValueError: If configuration is invalid or cleaning fails
        """
        try:
            if not self.data_input:
                raise ValueError(i18n.t("components.manipulations.data_cleaning.errors.no_data"))

            if not self.cleaning_rules:
                raise ValueError(i18n.t("components.manipulations.data_cleaning.errors.no_rules"))

            self.status = i18n.t("components.manipulations.data_cleaning.status.processing")

            result_data = []
            processed_count = 0

            # Process each data item
            # Handle both single Data objects and lists of Data objects
            data_items = self.data_input
            if not isinstance(data_items, list):
                data_items = [data_items]

            for data_item in data_items:
                # Get original data dictionary
                row_dict = data_item.data if hasattr(data_item, "data") and isinstance(data_item.data, dict) else data_item

                # If row_dict is still not a dict, try to handle it
                if not isinstance(row_dict, dict):
                    if isinstance(row_dict, tuple):
                        # Handle tuple case - try to extract meaningful data
                        logger.warning(f"Received tuple instead of dict: {row_dict}")
                        if len(row_dict) >= 2 and isinstance(row_dict[1], dict):
                            row_dict = row_dict[1]  # Use the second element if it's a dict
                        else:
                            logger.error(f"Cannot process tuple: {row_dict}")
                            continue
                    else:
                        logger.warning(f"Expected dict but got {type(row_dict)}: {row_dict}")
                        continue

                # 1. Evaluate filter conditions
                if not self._evaluate_filter_conditions(row_dict):
                    # Doesn't meet conditions, skip this record (filter it out)
                    continue

                # 2. Check max records limit
                if self.max_records > 0 and processed_count >= self.max_records:
                    # Exceeded limit, stop processing more records
                    break

                # 3. Apply cleaning rules
                cleaned_row = self._apply_cleaning_rules(row_dict)
                result_data.append(Data(data=cleaned_row))
                processed_count += 1

            self.status = i18n.t("components.manipulations.data_cleaning.status.success", count=processed_count)
            logger.info(f"[DataCleaning] Cleaned {processed_count} records out of {len(result_data)} total")

            return result_data

        except Exception as e:
            error_msg = i18n.t("components.manipulations.data_cleaning.errors.cleaning_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
