import re
import time
from dataclasses import dataclass
from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    HandleInput,
    Output,
    TableInput,
)
from lfx.log.logger import logger
from lfx.schema import Data

# Operator constants for conditional routing
OPERATOR_VALUES = [
    "equals",
    "not_equals",
    "contains",
    "starts_with",
    "ends_with",
    "regex",
    "less_than",
    "less_than_or_equal",
    "greater_than",
    "greater_than_or_equal",
    "is_empty",
    "is_not_empty",
    "in_list",
    "not_in_list",
]


@dataclass
class FieldInfo:
    """Information about an extracted field including type and sample values."""

    name: str
    type: str  # 'string', 'number', 'boolean', 'date'
    sample_values: list[Any] = None
    description: str = ""

    def __post_init__(self):
        if self.sample_values is None:
            self.sample_values = []


class ConditionalRouterComponent(Component):
    display_name = i18n.t("components.logic.conditional_router.display_name")
    description = i18n.t("components.logic.conditional_router.description")
    documentation: str = "https://docs.langflow.org/components-logic#conditional-router-if-else-component"
    icon = "split"
    name = "ConditionalRouter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__iteration_updated = False
        # Enhanced field extraction with caching
        self._field_cache: dict[str, tuple[list[FieldInfo], float]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._field_info_cache: dict[str, list[FieldInfo]] = {}

    inputs = [
        # New enhanced multi-condition inputs
        HandleInput(
            name="data_input",
            display_name=i18n.t("components.logic.conditional_router.data_input.display_name"),
            info=i18n.t("components.logic.conditional_router.data_input.info"),
            input_types=["Data", "Message"],
            required=True,
        ),
        TableInput(
            name="conditions",
            display_name=i18n.t("components.logic.conditional_router.conditions.display_name"),
            info=i18n.t("components.logic.conditional_router.conditions.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "display_name": i18n.t("components.logic.conditional_router.conditions.field_name"),
                    "type": "str",
                    # No options - allow free text input like compare_value
                },
                {
                    "name": "operator",
                    "display_name": i18n.t("components.logic.conditional_router.conditions.operator"),
                    "type": "str",
                    "options": OPERATOR_VALUES,
                    "options_metadata": [
                        {
                            "value": "equals",
                            "label": i18n.t("components.logic.conditional_router.operators.equals"),
                        },
                        {
                            "value": "not_equals",
                            "label": i18n.t("components.logic.conditional_router.operators.not_equals"),
                        },
                        {
                            "value": "contains",
                            "label": i18n.t("components.logic.conditional_router.operators.contains"),
                        },
                        {
                            "value": "starts_with",
                            "label": i18n.t("components.logic.conditional_router.operators.starts_with"),
                        },
                        {
                            "value": "ends_with",
                            "label": i18n.t("components.logic.conditional_router.operators.ends_with"),
                        },
                        {
                            "value": "regex",
                            "label": i18n.t("components.logic.conditional_router.operators.regex"),
                        },
                        {
                            "value": "less_than",
                            "label": i18n.t("components.logic.conditional_router.operators.less_than"),
                        },
                        {
                            "value": "less_than_or_equal",
                            "label": i18n.t("components.logic.conditional_router.operators.less_than_or_equal"),
                        },
                        {
                            "value": "greater_than",
                            "label": i18n.t("components.logic.conditional_router.operators.greater_than"),
                        },
                        {
                            "value": "greater_than_or_equal",
                            "label": i18n.t("components.logic.conditional_router.operators.greater_than_or_equal"),
                        },
                        {
                            "value": "is_empty",
                            "label": i18n.t("components.logic.conditional_router.operators.is_empty"),
                        },
                        {
                            "value": "is_not_empty",
                            "label": i18n.t("components.logic.conditional_router.operators.is_not_empty"),
                        },
                        {
                            "value": "in_list",
                            "label": i18n.t("components.logic.conditional_router.operators.in_list"),
                        },
                        {
                            "value": "not_in_list",
                            "label": i18n.t("components.logic.conditional_router.operators.not_in_list"),
                        },
                    ],
                },
                {
                    "name": "compare_value",
                    "display_name": i18n.t("components.logic.conditional_router.conditions.compare_value"),
                    "type": "str",
                    "info": i18n.t("components.logic.conditional_router.conditions.compare_value_info"),
                },
                {
                    "name": "combination_logic",
                    "display_name": i18n.t("components.logic.conditional_router.combination_logic.display_name"),
                    "type": "str",
                    "formatter": "text",
                    "options": ["AND", "OR"],
                    "options_metadata": [
                        {
                            "value": "AND",
                            "label": i18n.t("components.logic.conditional_router.combination_logic.and"),
                        },
                        {
                            "value": "OR",
                            "label": i18n.t("components.logic.conditional_router.combination_logic.or"),
                        },
                    ],
                    "info": i18n.t("components.logic.conditional_router.combination_logic.info"),
                },
            ],
            value=[],
            table_options={
                "block_add": False,
                "block_delete": False,
                "pagination": True,
                "action_buttons": [
                    {
                        "name": "load_fields",
                        "label": i18n.t("components.logic.conditional_router.conditions.load_fields_button"),
                        "icon": "Download",
                        "position": "top",
                    }
                ],
            },
            required=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t("components.logic.conditional_router.case_sensitive.display_name"),
            info=i18n.t("components.logic.conditional_router.case_sensitive.info"),
            value=True,
            advanced=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.logic.conditional_router.outputs.true_result.display_name"),
            name="true_result",
            method="true_response",
            group_outputs=True,
        ),
        Output(
            display_name=i18n.t("components.logic.conditional_router.outputs.false_result.display_name"),
            name="false_result",
            method="false_response",
            group_outputs=True,
        ),
    ]

    def _pre_run_setup(self):
        self.__iteration_updated = False
        logger.debug(i18n.t("components.logic.conditional_router.logs.multi_condition_mode_enabled"))
        logger.debug(i18n.t("components.logic.conditional_router.logs.pre_run_setup"))

    def extract_field_value(self, data: Any, field_path: str) -> Any:
        """Extract field value from data object using dot notation for nested fields.

        Args:
            data: The data object (Data, Message, dict, etc.)
            field_path: Field path with dot notation (e.g., "user.profile.name")

        Returns:
            Field value or None if not found
        """
        try:
            # Handle Message objects
            if hasattr(data, "text") and hasattr(data, "data"):
                # For Message objects, try to extract from data first, then text
                if hasattr(data, "data") and data.data:
                    value = self._extract_from_dict(data.data, field_path)
                    if value is not None:
                        return str(value)
                return data.text or ""

            # Handle Data objects
            if hasattr(data, "data"):
                if isinstance(data.data, list) and len(data.data) > 0:
                    # For Data objects with multiple rows, use first row
                    first_row = data.data[0]
                    if isinstance(first_row, dict):
                        value = self._extract_from_dict(first_row, field_path)
                        return str(value) if value is not None else ""
                elif isinstance(data.data, dict):
                    # First try to find the field directly in the dict
                    value = self._extract_from_dict(data.data, field_path)
                    if value is not None:
                        return str(value)

                    # If not found, look for it in nested lists within the dict
                    for key, nested_value in data.data.items():
                        if isinstance(nested_value, list) and len(nested_value) > 0:
                            first_item = nested_value[0]
                            if isinstance(first_item, dict):
                                value = self._extract_from_dict(first_item, field_path)
                                if value is not None:
                                    return str(value)

                    return ""

            # Handle plain dictionaries
            elif isinstance(data, dict):
                value = self._extract_from_dict(data, field_path)
                return str(value) if value is not None else ""

            # Handle plain strings/other types
            else:
                return str(data) if data is not None else ""

        except Exception as e:
            logger.warning(
                i18n.t(
                    "components.logic.conditional_router.warnings.field_extraction_error",
                    field_path=field_path,
                    error=str(e),
                )
            )
            return ""

    def _extract_from_dict(self, data_dict: dict, field_path: str) -> Any:
        """Extract value from dictionary using dot notation."""
        keys = field_path.split(".")
        value = data_dict

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _get_combination_logic(self) -> str:
        """Get combination logic from table_options or legacy input.

        Returns:
            "AND" or "OR" string for combination logic
        """
        # Try to get from table_options first (new way)
        try:
            conditions_input = next((inp for inp in self.inputs if inp.name == "conditions"), None)
            if conditions_input and hasattr(conditions_input, "table_options"):
                table_options = conditions_input.table_options
                if isinstance(table_options, dict) and "combination_logic" in table_options:
                    logic_config = table_options["combination_logic"]
                    if isinstance(logic_config, dict):
                        return logic_config.get("value", "AND")
        except Exception as e:
            logger.debug(f"Failed to get combination_logic from table_options: {e}")

        # Fallback to legacy attribute (backward compatibility)
        if hasattr(self, "combination_logic"):
            return self.combination_logic

        # Default to AND
        return "AND"

    def evaluate_conditions(self, input_data: Any) -> bool:
        """Evaluate multiple conditions with AND/OR logic.

        Args:
            input_data: The input data (Data, Message, or other object)

        Returns:
            Boolean result of condition evaluation
        """
        if not self.conditions:
            logger.warning(i18n.t("components.logic.conditional_router.warnings.no_conditions_configured"))
            return False

        # Evaluate all conditions with their individual combination logic
        results = []

        for condition in self.conditions:
            if not isinstance(condition, dict):
                continue

            field_name = condition.get("field_name", "")
            operator = condition.get("operator", "equals")
            compare_value = condition.get("compare_value", "")
            combination_logic = condition.get("combination_logic", "AND")  # Get from each row

            if not field_name:
                logger.warning(i18n.t("components.logic.conditional_router.warnings.empty_field_name"))
                continue

            # Extract field value from input data
            field_value = self.extract_field_value(input_data, field_name)

            # Evaluate single condition
            result = self.evaluate_condition(field_value, compare_value, operator, case_sensitive=self.case_sensitive)

            results.append((result, combination_logic))

            logger.debug(
                i18n.t(
                    "components.logic.conditional_router.logs.condition_evaluated",
                    field=field_name,
                    operator=operator,
                    value=field_value,
                    compare=compare_value,
                    result=result,
                )
            )

        # Compute final result based on individual combination logic operators
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

        logger.debug(
            i18n.t(
                "components.logic.conditional_router.logs.final_evaluation",
                logic="sequential",
                results=results,
                final_result=final_result,
            )
        )

        return final_result

    def evaluate_condition(self, input_text: str, match_text: str, operator: str, *, case_sensitive: bool) -> bool:
        logger.debug(
            i18n.t(
                "components.logic.conditional_router.logs.evaluating", operator=operator, case_sensitive=case_sensitive
            )
        )

        if not case_sensitive and operator != "regex":
            input_text = input_text.lower()
            match_text = match_text.lower()

        result = False

        if operator == "equals":
            result = input_text == match_text
        elif operator == "not_equals":
            result = input_text != match_text
        elif operator == "contains":
            result = match_text in input_text
        elif operator == "starts_with":
            result = input_text.startswith(match_text)
        elif operator == "ends_with":
            result = input_text.endswith(match_text)
        elif operator == "regex":
            try:
                result = bool(re.match(match_text, input_text))
            except re.error as e:
                logger.warning(
                    i18n.t(
                        "components.logic.conditional_router.warnings.invalid_regex", pattern=match_text, error=str(e)
                    )
                )
                return False
        elif operator in ["less_than", "less_than_or_equal", "greater_than", "greater_than_or_equal"]:
            try:
                input_num = float(input_text)
                match_num = float(match_text)
                if operator == "less_than":
                    result = input_num < match_num
                elif operator == "less_than_or_equal":
                    result = input_num <= match_num
                elif operator == "greater_than":
                    result = input_num > match_num
                elif operator == "greater_than_or_equal":
                    result = input_num >= match_num
            except ValueError as e:
                logger.warning(
                    i18n.t(
                        "components.logic.conditional_router.warnings.invalid_number",
                        input_text=input_text,
                        match_text=match_text,
                        error=str(e),
                    )
                )
                return False
        elif operator == "is_empty":
            result = not input_text or input_text.strip() == ""
        elif operator == "is_not_empty":
            result = bool(input_text and input_text.strip())
        elif operator == "in_list":
            try:
                # Parse compare_value as a comma-separated list
                value_list = [item.strip() for item in match_text.split(",")]
                result = input_text in value_list
            except Exception as e:
                logger.warning(
                    i18n.t(
                        "components.logic.conditional_router.warnings.invalid_list",
                        match_text=match_text,
                        error=str(e),
                    )
                )
                return False
        elif operator == "not_in_list":
            try:
                # Parse compare_value as a comma-separated list
                value_list = [item.strip() for item in match_text.split(",")]
                result = input_text not in value_list
            except Exception as e:
                logger.warning(
                    i18n.t(
                        "components.logic.conditional_router.warnings.invalid_list",
                        match_text=match_text,
                        error=str(e),
                    )
                )
                return False

        logger.debug(i18n.t("components.logic.conditional_router.logs.evaluation_result", result=result))
        return result

    def iterate_and_stop_once(self, route_to_stop: str):
        """Handles cycle iteration counting and branch exclusion.

        Uses two complementary mechanisms:
        1. stop() - ACTIVE/INACTIVE state for cycle management (gets reset each iteration)
        2. exclude_branch_conditionally() - Persistent exclusion for conditional routing

        When max_iterations is reached, breaks the cycle by allowing the default_route to execute.
        """
        if not self.__iteration_updated:
            current_iteration = self.ctx.get(f"{self._id}_iteration", 0) + 1
            self.update_ctx({f"{self._id}_iteration": current_iteration})
            self.__iteration_updated = True

            logger.debug(
                i18n.t(
                    "components.logic.conditional_router.logs.iteration_updated",
                    iteration=current_iteration,
                    max_iterations=self.max_iterations,
                )
            )

            # Check if max iterations reached and we're trying to stop the default route
            if current_iteration >= self.max_iterations and route_to_stop == self.default_route:
                logger.info(
                    i18n.t(
                        "components.logic.conditional_router.logs.max_iterations_reached",
                        iteration=current_iteration,
                        default_route=self.default_route,
                    )
                )

                # Clear ALL conditional exclusions to allow default route to execute
                if self._id in self.graph.conditional_exclusion_sources:
                    previous_exclusions = self.graph.conditional_exclusion_sources[self._id]
                    self.graph.conditionally_excluded_vertices -= previous_exclusions
                    del self.graph.conditional_exclusion_sources[self._id]
                    logger.debug(
                        i18n.t(
                            "components.logic.conditional_router.logs.cleared_exclusions",
                            count=len(previous_exclusions),
                        )
                    )

                # Switch which route to stop - stop the NON-default route to break the cycle
                route_to_stop = "true_result" if route_to_stop == "false_result" else "false_result"
                logger.debug(i18n.t("components.logic.conditional_router.logs.switched_route", new_route=route_to_stop))

                # Call stop to break the cycle
                self.stop(route_to_stop)
                # Don't apply conditional exclusion when breaking cycle
                return

            # Normal case: Use BOTH mechanisms
            logger.debug(i18n.t("components.logic.conditional_router.logs.stopping_route", route=route_to_stop))

            # 1. stop() for cycle management (marks INACTIVE, updates run manager, gets reset)
            self.stop(route_to_stop)

            # 2. Conditional exclusion for persistent routing (doesn't get reset except by this router)
            self.graph.exclude_branch_conditionally(self._id, output_name=route_to_stop)

    def true_response(self) -> list[Data]:
        """Filter data and return items that match the conditions."""
        input_data = getattr(self, "data_input", None)

        # Handle list of Data objects
        if isinstance(input_data, list):
            true_list = []

            for data_item in input_data:
                # Evaluate conditions for this data item
                result = self.evaluate_conditions(data_item)

                if result:
                    true_list.append(data_item)

            # Update status with count
            self.status = i18n.t(
                "components.logic.conditional_router.status.multi_condition_true",
                logic="filter",
                conditions=len(true_list),
            )
            logger.debug(f"Filtered {len(true_list)} items to true output")

            # In data filtering mode, don't stop the other branch
            # Both branches should execute and return their filtered data
            return true_list

        # Single data item
        result = self.evaluate_conditions(input_data)

        if result:
            self.status = i18n.t("components.logic.conditional_router.status.condition_true")
            logger.debug(i18n.t("components.logic.conditional_router.logs.condition_true"))

            # Return single item as list
            if hasattr(input_data, "data"):
                return [input_data]
            if isinstance(input_data, dict):
                return [Data(data=input_data)]
            return [Data(data={"value": str(input_data)})]

        return []

    def false_response(self) -> list[Data]:
        """Filter data and return items that don't match the conditions."""
        input_data = getattr(self, "data_input", None)

        # Handle list of Data objects
        if isinstance(input_data, list):
            false_list = []

            for data_item in input_data:
                # Evaluate conditions for this data item
                result = self.evaluate_conditions(data_item)

                if not result:
                    false_list.append(data_item)

            # Update status with count
            self.status = i18n.t(
                "components.logic.conditional_router.status.multi_condition_false",
                logic="filter",
                conditions=len(false_list),
            )
            logger.debug(f"Filtered {len(false_list)} items to false output")

            # In data filtering mode, don't stop the other branch
            # Both branches should execute and return their filtered data
            return false_list

        # Single data item
        result = self.evaluate_conditions(input_data)

        if not result:
            self.status = i18n.t("components.logic.conditional_router.status.condition_false")
            logger.debug(i18n.t("components.logic.conditional_router.logs.condition_false"))

            # Return single item as list
            if hasattr(input_data, "data"):
                return [input_data]
            if isinstance(input_data, dict):
                return [Data(data=input_data)]
            return [Data(data={"value": str(input_data)})]

        return []

    async def update_build_config(
        self, build_config: dict, field_value: str, field_name: str | None = None, action: str | None = None
    ) -> dict:
        # Handle load_fields action for populating field options
        if action == "load_fields" and field_name == "conditions":
            logger.debug(i18n.t("components.logic.conditional_router.logs.loading_fields"))
            try:
                # Get graph_data and node_id from build_config
                graph_data = build_config.get("_graph_data", {})
                node_id = build_config.get("_node_id")

                # Fallback to self.graph if available
                if not graph_data and hasattr(self, "graph") and self.graph is not None:
                    if hasattr(self.graph, "data"):
                        graph_data = self.graph.data
                    else:
                        logger.warning(i18n.t("components.logic.conditional_router.warnings.no_graph_data_placeholder"))

                if not graph_data:
                    logger.warning(i18n.t("components.logic.conditional_router.logs.no_graph_data"))
                    self.status = i18n.t("components.logic.conditional_router.errors.no_graph_data_error")
                    return build_config

                field_options = []

                # PRIMARY STRATEGY: Try static field extraction from upstream schema (FAST, RELIABLE)
                try:
                    from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

                    fields = find_and_extract_upstream_fields(graph_data, node_id, "data_input", "ConditionalRouter")

                    if fields:
                        field_options = [field["name"] for field in fields]
                        logger.debug(
                            i18n.t(
                                "components.logic.conditional_router.logs.fields_from_template",
                                count=len(field_options),
                            )
                        )

                except Exception as static_error:
                    logger.debug(
                        i18n.t(
                            "components.logic.conditional_router.warnings.static_extraction_failed",
                            error=str(static_error),
                        )
                    )

                # FALLBACK STRATEGY: Try to execute upstream node to get actual data (SLOW, MAY FAIL)
                if not field_options:
                    logger.debug(i18n.t("components.logic.conditional_router.logs.trying_data_extraction"))
                    try:
                        upstream_data = await self.get_upstream_data(
                            input_name="data_input", graph_data=graph_data, sample_size=10, vertex_id=node_id
                        )

                        if upstream_data:
                            # Extract field information from upstream data
                            field_info_list = self.extract_field_info_with_types(upstream_data)
                            field_options = [info.name for info in field_info_list]
                            logger.debug(
                                i18n.t(
                                    "components.logic.conditional_router.logs.fields_from_data",
                                    count=len(field_options),
                                )
                            )
                        else:
                            logger.warning(i18n.t("components.logic.conditional_router.warnings.no_upstream_data"))

                    except Exception as e:
                        # Upstream execution failed
                        logger.debug(
                            i18n.t(
                                "components.logic.conditional_router.warnings.upstream_failed",
                                error=str(e),
                            )
                        )

                # Update build_config with auto-filled table rows
                if field_options and "conditions" in build_config:
                    # Auto-fill table with one row per field, default operator is "equals"
                    auto_filled_rows = [
                        {
                            "field_name": field_name,
                            "operator": "equals",  # Default operator
                            "compare_value": "",  # Empty by default
                            "combination_logic": "AND",  # Default combination logic
                        }
                        for field_name in field_options
                    ]
                    build_config["conditions"]["value"] = auto_filled_rows
                    self.status = i18n.t(
                        "components.logic.conditional_router.status.fields_loaded", count=len(field_options)
                    )
                else:
                    self.status = i18n.t("components.logic.conditional_router.warnings.no_fields_found_error")

            except Exception as e:
                logger.warning(i18n.t("components.logic.conditional_router.warnings.field_loading_error", error=str(e)))
                self.status = i18n.t("components.logic.conditional_router.errors.field_loading_failed", error=str(e))

            return build_config

        if field_name == "operator":
            logger.debug(i18n.t("components.logic.conditional_router.logs.updating_config", operator=field_value))

            if field_value == "regex":
                build_config.pop("case_sensitive", None)
                logger.debug(i18n.t("components.logic.conditional_router.logs.removed_case_sensitive"))
            elif "case_sensitive" not in build_config:
                case_sensitive_input = next(
                    (input_field for input_field in self.inputs if input_field.name == "case_sensitive"), None
                )
                if case_sensitive_input:
                    build_config["case_sensitive"] = case_sensitive_input.to_dict()
                    logger.debug(i18n.t("components.logic.conditional_router.logs.added_case_sensitive"))
        elif field_name == "combination_logic":
            logger.debug(
                i18n.t("components.logic.conditional_router.logs.updating_combination_logic", logic=field_value)
            )
        elif field_name == "conditions":
            logger.debug(
                i18n.t(
                    "components.logic.conditional_router.logs.updating_conditions",
                    conditions_count=len(field_value) if field_value else 0,
                )
            )
        return build_config

    def populate_field_options(self) -> list[str]:
        """Populate field options from upstream data schema.

        Returns:
            List of field names available in upstream data
        """
        try:
            # Check if we have graph data available
            if not hasattr(self, "graph") or not self.graph:
                logger.debug(i18n.t("components.logic.conditional_router.logs.no_graph_available"))
                return []

            # Get graph data for field extraction
            graph_data = getattr(self.graph, "data", {})
            if not graph_data:
                logger.debug(i18n.t("components.logic.conditional_router.logs.no_graph_data"))
                return []

            # Extract fields from upstream data_input
            field_names = []

            # Try to get upstream data if available (for enhanced real-time field extraction)
            try:
                if hasattr(self, "data_input") and self.data_input:
                    # Use enhanced field extraction with type inference
                    field_info_list = self.extract_field_info_with_types(self.data_input)
                    if field_info_list:
                        field_names = [info.name for info in field_info_list]
                        logger.info(
                            i18n.t("components.logic.conditional_router.logs.fields_from_data", count=len(field_names))
                        )
                        # Update field types in the component for smart operator suggestions
                        self.enhance_conditions_with_field_types()
                        return field_names
            except Exception as e:
                logger.debug(f"Failed to extract fields from data_input: {e}")

            # Fallback to field extraction from template configuration
            from lfx.components.helpers.field_extraction import find_and_extract_upstream_fields

            fields = find_and_extract_upstream_fields(graph_data, self._id, "data_input", "ConditionalRouter")

            if fields:
                field_names = [field["name"] for field in fields]
                logger.info(
                    i18n.t("components.logic.conditional_router.logs.fields_from_template", count=len(field_names))
                )
            else:
                logger.debug(i18n.t("components.logic.conditional_router.logs.no_fields_found"))

            return field_names

        except Exception as e:
            logger.warning(i18n.t("components.logic.conditional_router.warnings.field_population_error", error=str(e)))
            return []

    def get_field_options(self) -> list[str]:
        """Get field options for dropdown population.

        This method can be called by the frontend to populate field dropdown options.

        Returns:
            List of available field names
        """
        return self.populate_field_options()

    def update_field_options(self) -> None:
        """Update the field options in the conditions table schema.

        This method can be called to refresh field options when upstream connections change.
        """
        try:
            field_options = self.populate_field_options()

            # Update the conditions table schema field_name options
            conditions_input = None
            for input_field in self.inputs:
                if input_field.name == "conditions":
                    conditions_input = input_field
                    break

            if conditions_input and hasattr(conditions_input, "table_schema"):
                # Find the field_name column and update its options
                for column in conditions_input.table_schema:
                    if column.get("name") == "field_name":
                        column["options"] = field_options
                        logger.debug(
                            i18n.t(
                                "components.logic.conditional_router.logs.field_options_updated",
                                count=len(field_options),
                            )
                        )
                        break

        except Exception as e:
            logger.warning(
                i18n.t("components.logic.conditional_router.warnings.update_field_options_error", error=str(e))
            )

    def infer_field_type(self, field_name: str, sample_values: list[Any]) -> str:
        """Infer the type of a field based on sample values.

        Args:
            field_name: Name of the field
            sample_values: List of sample values from the field

        Returns:
            Field type: 'string', 'number', 'boolean', 'date'
        """
        if not sample_values:
            return "string"

        # Analyze sample values
        numeric_count = 0
        boolean_count = 0
        date_count = 0
        string_count = 0

        for value in sample_values:
            if value is None or value == "":
                continue

            # Check for boolean
            if isinstance(value, bool) or str(value).lower() in ("true", "false", "yes", "no", "1", "0"):
                boolean_count += 1
            # Check for numeric
            elif self._is_numeric(value):
                numeric_count += 1
            # Check for date
            elif self._is_date_like(value):
                date_count += 1
            # Default to string
            else:
                string_count += 1

        # Determine type based on majority
        total = numeric_count + boolean_count + date_count + string_count
        if total == 0:
            return "string"

        if numeric_count / total > 0.7:
            return "number"
        if boolean_count / total > 0.7:
            return "boolean"
        if date_count / total > 0.7:
            return "date"
        return "string"

    def _is_numeric(self, value: Any) -> bool:
        """Check if a value can be interpreted as numeric."""
        try:
            float(str(value))
            return True
        except (ValueError, TypeError):
            return False

    def _is_date_like(self, value: Any) -> bool:
        """Check if a value looks like a date."""
        import datetime

        date_patterns = [
            r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
            r"\d{2}-\d{2}-\d{4}",  # MM-DD-YYYY
        ]

        value_str = str(value)
        for pattern in date_patterns:
            if re.match(pattern, value_str):
                return True

        # Try to parse as date
        for date_format in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d %H:%M:%S"]:
            try:
                datetime.datetime.strptime(value_str, date_format)
                return True
            except ValueError:
                continue

        return False

    def extract_field_info_with_types(self, data: Any) -> list[FieldInfo]:
        """Extract field information including types and sample values.

        Args:
            data: The data object to analyze

        Returns:
            List of FieldInfo objects with type information
        """
        cache_key = self._get_cache_key(data)

        # Check cache first
        if cache_key in self._field_info_cache:
            cached_time, cached_fields = self._field_info_cache.get(cache_key, ([], 0))
            if isinstance(cached_time, (int, float)) and time.time() - cached_time < self._cache_ttl:
                logger.debug(f"Using cached field info for {len(cached_fields)} fields")
                return cached_fields

        field_info_list = []
        sample_data = self._extract_sample_data(data)

        if not sample_data:
            return field_info_list

        # Extract all field paths from sample data
        all_field_paths = set()
        for sample in sample_data:
            if isinstance(sample, dict):
                paths = self._extract_all_field_paths(sample)
                all_field_paths.update(paths)

        # Create field info for each field
        for field_path in sorted(all_field_paths):
            sample_values = []
            for sample in sample_data:
                value = self._extract_from_dict(sample, field_path)
                if value is not None:
                    sample_values.append(value)

            field_type = self.infer_field_type(field_path, sample_values)
            field_info = FieldInfo(
                name=field_path,
                type=field_type,
                sample_values=sample_values[:5],  # Keep only first 5 samples
            )
            field_info_list.append(field_info)

        # Cache the results
        self._field_info_cache[cache_key] = field_info_list
        self._field_cache[cache_key] = (field_info_list, time.time())

        logger.info(f"Extracted {len(field_info_list)} fields with type information")
        return field_info_list

    def _extract_sample_data(self, data: Any) -> list[dict]:
        """Extract sample data for field analysis."""
        samples = []

        try:
            # Handle Data objects
            if hasattr(data, "data"):
                if isinstance(data.data, list):
                    samples = data.data[:10]  # Limit to 10 samples
                elif isinstance(data.data, dict):
                    # Look for lists within the dict (e.g., {"records": [...]})
                    found_list = False
                    for key, value in data.data.items():
                        if isinstance(value, list) and value:
                            samples = value[:10]  # Limit to 10 samples
                            found_list = True
                            break
                    if not found_list:
                        samples = [data.data]

            # Handle Message objects
            elif hasattr(data, "text"):
                if hasattr(data, "data") and isinstance(data.data, dict):
                    samples = [data.data]
                else:
                    # Create a simple structure with text
                    samples = [{"text": data.text or ""}]

            # Handle plain dictionaries
            elif isinstance(data, dict):
                samples = [data]

            # Handle lists
            elif isinstance(data, list):
                # Process list items - they might be Data objects
                for item in data[:10]:
                    if hasattr(item, "data") and isinstance(item.data, dict):
                        # Item is a Data object, extract its data
                        samples.append(item.data)
                    elif isinstance(item, dict):
                        # Item is already a dict
                        samples.append(item)
                    # Skip other types

        except Exception as e:
            logger.warning(f"Error extracting sample data: {e}")

        return [s for s in samples if s]  # Filter out None values

    def _extract_all_field_paths(self, data: dict, prefix: str = "") -> list[str]:
        """Extract all field paths from a nested dictionary."""
        paths = []

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict) and value:
                # Recursively extract nested fields
                nested_paths = self._extract_all_field_paths(value, current_path)
                paths.extend(nested_paths)
            else:
                paths.append(current_path)

        return paths

    def _get_cache_key(self, data: Any) -> str:
        """Generate a cache key for the given data."""
        try:
            # Create a simple hash based on data structure
            if hasattr(data, "data"):
                if isinstance(data.data, list) and data.data:
                    # Use first item as representative
                    return str(hash(str(data.data[0])))
                if isinstance(data.data, dict):
                    return str(hash(str(data.data)))
            elif isinstance(data, dict):
                return str(hash(str(data)))
            else:
                return str(hash(str(data)))
        except Exception:
            # Fallback to timestamp-based key
            return f"cache_{int(time.time() // 60)}"  # Cache per minute

    def get_operators_for_field_type(self, field_type: str) -> list[str]:
        """Get appropriate operators for a given field type.

        Args:
            field_type: The field type ('string', 'number', 'boolean', 'date')

        Returns:
            List of suitable operators for the field type
        """
        operators = {
            "string": [
                "equals",
                "not_equals",
                "contains",
                "starts_with",
                "ends_with",
                "regex",
                "is_empty",
                "is_not_empty",
                "in_list",
                "not_in_list",
            ],
            "number": [
                "equals",
                "not_equals",
                "less_than",
                "less_than_or_equal",
                "greater_than",
                "greater_than_or_equal",
                "is_empty",
                "is_not_empty",
            ],
            "boolean": ["equals", "not_equals", "is_empty", "is_not_empty"],
            "date": [
                "equals",
                "not_equals",
                "less_than",
                "less_than_or_equal",
                "greater_than",
                "greater_than_or_equal",
                "is_empty",
                "is_not_empty",
            ],
        }

        return operators.get(field_type, operators["string"])

    def enhance_conditions_with_field_types(self):
        """Enhance the conditions table with field type information."""
        try:
            if not hasattr(self, "data_input") or not self.data_input:
                return

            # Extract field info from upstream data
            field_info_list = self.extract_field_info_with_types(self.data_input)

            # Update conditions table schema with field types
            conditions_input = None
            for input_field in self.inputs:
                if input_field.name == "conditions":
                    conditions_input = input_field
                    break

            if conditions_input and hasattr(conditions_input, "table_schema"):
                # Update field_types in schema
                field_types = {info.name: info.type for info in field_info_list}

                for column in conditions_input.table_schema:
                    if column.get("name") == "field_name":
                        column["field_types"] = field_types
                        # Update options with field names only
                        column["options"] = [info.name for info in field_info_list]
                        break

                logger.debug(f"Updated conditions table with {len(field_info_list)} field types")

        except Exception as e:
            logger.warning(f"Error enhancing conditions with field types: {e}")
