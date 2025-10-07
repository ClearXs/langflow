from typing import Any, Dict, List, Union, Optional
import json
import operator
from datetime import datetime, date
from decimal import Decimal
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    MultilineInput,
    IntInput,
    FloatInput
)
from lfx.schema.data import Data
from lfx.template.field.base import Output


class DataConditionalRouterComponent(Component):
    display_name = i18n.t(
        'components.logic.data_conditional_router.display_name')
    description = i18n.t(
        'components.logic.data_conditional_router.description')
    documentation: str = "https://docs.langflow.org/components-logic#data-conditional-router"
    icon = "GitBranch"
    name = "DataConditionalRouter"

    inputs = [
        HandleInput(
            name="input_data",
            display_name=i18n.t(
                'components.logic.data_conditional_router.input_data.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.input_data.info'),
            input_types=["Data"],
            required=True,
        ),
        MultilineInput(
            name="routing_rules",
            display_name=i18n.t(
                'components.logic.data_conditional_router.routing_rules.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.routing_rules.info'),
            placeholder='[\n  {\n    "name": "high_priority",\n    "conditions": [\n      {"field": "priority", "operator": ">=", "value": 5},\n      {"field": "status", "operator": "==", "value": "active"}\n    ],\n    "logic": "AND"\n  }\n]',
            required=True,
        ),
        DropdownInput(
            name="evaluation_strategy",
            display_name=i18n.t(
                'components.logic.data_conditional_router.evaluation_strategy.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.evaluation_strategy.info'),
            options=["first_match", "all_matches",
                     "priority_based", "score_based"],
            value="first_match",
            advanced=True,
        ),
        MessageTextInput(
            name="default_route",
            display_name=i18n.t(
                'components.logic.data_conditional_router.default_route.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.default_route.info'),
            value="default",
            advanced=True,
        ),
        BoolInput(
            name="strict_typing",
            display_name=i18n.t(
                'components.logic.data_conditional_router.strict_typing.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.strict_typing.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="null_safe_comparison",
            display_name=i18n.t(
                'components.logic.data_conditional_router.null_safe_comparison.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.null_safe_comparison.info'),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="max_routes",
            display_name=i18n.t(
                'components.logic.data_conditional_router.max_routes.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.max_routes.info'),
            value=0,
            range_spec=(0, 100),
            advanced=True,
        ),
        BoolInput(
            name="include_route_metadata",
            display_name=i18n.t(
                'components.logic.data_conditional_router.include_route_metadata.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.include_route_metadata.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="fail_on_no_match",
            display_name=i18n.t(
                'components.logic.data_conditional_router.fail_on_no_match.display_name'),
            info=i18n.t(
                'components.logic.data_conditional_router.fail_on_no_match.info'),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.data_conditional_router.outputs.routed_data.display_name'),
            name="routed_data",
            method="route_data",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.data_conditional_router.outputs.routing_summary.display_name'),
            name="routing_summary",
            method="get_routing_summary",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.data_conditional_router.outputs.matched_rules.display_name'),
            name="matched_rules",
            method="get_matched_rules",
        ),
    ]

    # Supported operators
    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
        "contains": lambda a, b: b in str(a),
        "not_contains": lambda a, b: b not in str(a),
        "starts_with": lambda a, b: str(a).startswith(str(b)),
        "ends_with": lambda a, b: str(a).endswith(str(b)),
        "regex": lambda a, b: bool(__import__('re').search(str(b), str(a))),
        "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
        "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
        "is_null": lambda a, b: a is None,
        "is_not_null": lambda a, b: a is not None,
        "between": lambda a, b: b[0] <= a <= b[1] if isinstance(b, (list, tuple)) and len(b) == 2 else False,
    }

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "evaluation_strategy":
            if field_value in ["all_matches", "score_based"]:
                build_config["max_routes"]["show"] = True
            else:
                build_config["max_routes"]["show"] = False

        if field_name == "fail_on_no_match":
            if field_value:
                build_config["default_route"]["show"] = False
            else:
                build_config["default_route"]["show"] = True

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        if not self.routing_rules or not self.routing_rules.strip():
            error_message = i18n.t(
                'components.logic.data_conditional_router.errors.empty_routing_rules')
            self.status = error_message
            raise ValueError(error_message)

        if not isinstance(self.input_data, Data):
            error_message = i18n.t(
                'components.logic.data_conditional_router.errors.invalid_input_data')
            self.status = error_message
            raise ValueError(error_message)

        try:
            rules = json.loads(self.routing_rules)
            if not isinstance(rules, list):
                raise ValueError("Routing rules must be a list")

            if not rules:
                raise ValueError("At least one routing rule is required")

            for i, rule in enumerate(rules):
                self._validate_rule(rule, i)

        except (json.JSONDecodeError, ValueError) as e:
            error_message = i18n.t('components.logic.data_conditional_router.errors.invalid_routing_rules_format',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _validate_rule(self, rule: Dict[str, Any], index: int) -> None:
        """Validate a single routing rule."""
        if not isinstance(rule, dict):
            raise ValueError(f"Rule {index} must be an object")

        required_fields = ["name", "conditions"]
        for field in required_fields:
            if field not in rule:
                raise ValueError(f"Rule {index} must have '{field}' field")

        if not isinstance(rule["conditions"], list):
            raise ValueError(f"Rule {index} conditions must be a list")

        logic = rule.get("logic", "AND").upper()
        if logic not in ["AND", "OR"]:
            raise ValueError(f"Rule {index} logic must be 'AND' or 'OR'")

        for j, condition in enumerate(rule["conditions"]):
            if not isinstance(condition, dict):
                raise ValueError(
                    f"Rule {index} condition {j} must be an object")

            required_condition_fields = ["field", "operator"]
            for field in required_condition_fields:
                if field not in condition:
                    raise ValueError(
                        f"Rule {index} condition {j} must have '{field}' field")

            if condition["operator"] not in self.OPERATORS:
                valid_operators = list(self.OPERATORS.keys())
                raise ValueError(
                    f"Rule {index} condition {j} has invalid operator. Valid operators: {valid_operators}")

    def _get_field_value(self, data: Data, field_path: str) -> Any:
        """Get field value from data using dot notation."""
        try:
            if not hasattr(data, 'data'):
                return None

            value = data.data
            for field in field_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(field)
                elif hasattr(value, field):
                    value = getattr(value, field)
                else:
                    return None

                if value is None:
                    return None

            return value

        except Exception:
            return None

    def _convert_value_type(self, value: Any, target_value: Any) -> Any:
        """Convert value to match target type if strict typing is enabled."""
        if not self.strict_typing or target_value is None:
            return value

        try:
            target_type = type(target_value)

            if target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes', 'on']
                return bool(value)
            elif target_type == int:
                return int(float(value))  # Handle "5.0" -> 5
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return str(value)
            elif target_type in [list, tuple, set]:
                if isinstance(value, str):
                    # Try to parse as JSON
                    try:
                        parsed = json.loads(value)
                        return target_type(parsed) if isinstance(parsed, (list, tuple)) else value
                    except json.JSONDecodeError:
                        return value

            return value

        except (ValueError, TypeError):
            return value

    def _evaluate_condition(self, condition: Dict[str, Any], data: Data) -> bool:
        """Evaluate a single condition against the data."""
        try:
            field_path = condition["field"]
            operator_name = condition["operator"]
            expected_value = condition.get("value")

            # Get field value
            actual_value = self._get_field_value(data, field_path)

            # Handle null-safe comparison
            if self.null_safe_comparison:
                if operator_name == "is_null":
                    return actual_value is None
                elif operator_name == "is_not_null":
                    return actual_value is not None
                elif actual_value is None and operator_name not in ["is_null", "is_not_null"]:
                    return False

            # Convert types if needed
            if expected_value is not None:
                actual_value = self._convert_value_type(
                    actual_value, expected_value)

            # Get operator function
            operator_func = self.OPERATORS[operator_name]

            # Special handling for operators that don't need expected_value
            if operator_name in ["is_null", "is_not_null"]:
                return operator_func(actual_value, None)

            # Evaluate condition
            return operator_func(actual_value, expected_value)

        except Exception as e:
            warning_message = i18n.t('components.logic.data_conditional_router.warnings.condition_evaluation_error',
                                     field=condition.get("field", "unknown"), error=str(e))
            self.status = warning_message
            return False

    def _evaluate_rule(self, rule: Dict[str, Any], data: Data) -> Dict[str, Any]:
        """Evaluate a routing rule against the data."""
        conditions = rule["conditions"]
        logic = rule.get("logic", "AND").upper()

        results = []
        for condition in conditions:
            result = self._evaluate_condition(condition, data)
            results.append(result)

        # Apply logic
        if logic == "AND":
            matched = all(results)
        else:  # OR
            matched = any(results)

        return {
            "name": rule["name"],
            "matched": matched,
            "description": rule.get("description", ""),
            "priority": rule.get("priority", 0),
            "score": rule.get("score", 1.0),
            "conditions_evaluated": len(conditions),
            "conditions_passed": sum(results),
            "logic": logic,
            "timestamp": datetime.now().isoformat(),
        }

    def _select_routes(self, rule_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select which routes to use based on evaluation strategy."""
        matched_rules = [rule for rule in rule_results if rule["matched"]]

        if not matched_rules:
            return []

        if self.evaluation_strategy == "first_match":
            return [matched_rules[0]]

        elif self.evaluation_strategy == "all_matches":
            if self.max_routes > 0:
                return matched_rules[:self.max_routes]
            return matched_rules

        elif self.evaluation_strategy == "priority_based":
            # Sort by priority (highest first)
            sorted_rules = sorted(
                matched_rules, key=lambda x: x["priority"], reverse=True)
            if self.max_routes > 0:
                return sorted_rules[:self.max_routes]
            return sorted_rules

        elif self.evaluation_strategy == "score_based":
            # Sort by score (highest first)
            sorted_rules = sorted(
                matched_rules, key=lambda x: x["score"], reverse=True)
            if self.max_routes > 0:
                return sorted_rules[:self.max_routes]
            return sorted_rules

        return matched_rules

    def route_data(self) -> List[Data]:
        """Route data based on conditions."""
        try:
            self._validate_inputs()

            # Parse routing rules
            rules = json.loads(self.routing_rules)

            # Evaluate all rules
            rule_results = []
            for rule in rules:
                result = self._evaluate_rule(rule, self.input_data)
                rule_results.append(result)

            # Select routes based on strategy
            selected_routes = self._select_routes(rule_results)

            results = []

            if selected_routes:
                # Create routed data for each selected route
                for route in selected_routes:
                    route_data = {
                        "route_name": route["name"],
                        "original_data": self.input_data.data if hasattr(self.input_data, 'data') else self.input_data,
                        "route_matched": True,
                    }

                    if self.include_route_metadata:
                        route_data["route_metadata"] = {
                            "description": route["description"],
                            "priority": route["priority"],
                            "score": route["score"],
                            "conditions_evaluated": route["conditions_evaluated"],
                            "conditions_passed": route["conditions_passed"],
                            "logic": route["logic"],
                            "evaluation_strategy": self.evaluation_strategy,
                            "timestamp": route["timestamp"],
                        }

                    results.append(Data(data=route_data))

                success_message = i18n.t('components.logic.data_conditional_router.success.routes_matched',
                                         count=len(selected_routes))
                self.status = success_message

            else:
                # No matches
                if self.fail_on_no_match:
                    error_message = i18n.t(
                        'components.logic.data_conditional_router.errors.no_matches_fail_mode')
                    self.status = error_message
                    raise ValueError(error_message)
                else:
                    # Use default route
                    route_data = {
                        "route_name": self.default_route,
                        "original_data": self.input_data.data if hasattr(self.input_data, 'data') else self.input_data,
                        "route_matched": False,
                    }

                    if self.include_route_metadata:
                        route_data["route_metadata"] = {
                            "description": "Default route - no conditions matched",
                            "evaluation_strategy": self.evaluation_strategy,
                            "timestamp": datetime.now().isoformat(),
                            "total_rules_evaluated": len(rules),
                        }

                    results.append(Data(data=route_data))

                    warning_message = i18n.t('components.logic.data_conditional_router.warnings.using_default_route',
                                             route=self.default_route)
                    self.status = warning_message

            return results

        except Exception as e:
            error_message = i18n.t(
                'components.logic.data_conditional_router.errors.routing_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_routing_summary(self) -> Data:
        """Get summary of routing evaluation."""
        try:
            rules = json.loads(self.routing_rules)
            rule_results = []

            for rule in rules:
                result = self._evaluate_rule(rule, self.input_data)
                rule_results.append(result)

            matched_count = sum(
                1 for result in rule_results if result["matched"])

            summary = {
                "total_rules": len(rules),
                "matched_rules": matched_count,
                "evaluation_strategy": self.evaluation_strategy,
                "strict_typing": self.strict_typing,
                "null_safe_comparison": self.null_safe_comparison,
                "fail_on_no_match": self.fail_on_no_match,
                "default_route": self.default_route,
                "timestamp": datetime.now().isoformat(),
                "rule_results": rule_results,
            }

            return Data(data=summary)

        except Exception as e:
            error_message = i18n.t('components.logic.data_conditional_router.errors.routing_summary_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_matched_rules(self) -> List[Data]:
        """Get list of all matched rules."""
        try:
            rules = json.loads(self.routing_rules)
            rule_results = []

            for rule in rules:
                result = self._evaluate_rule(rule, self.input_data)
                if result["matched"]:
                    rule_results.append(result)

            if not rule_results:
                return [Data(data={
                    "route_name": self.default_route,
                    "matched": False,
                    "is_default": True,
                    "timestamp": datetime.now().isoformat(),
                })]

            return [Data(data=result) for result in rule_results]

        except Exception as e:
            error_message = i18n.t('components.logic.data_conditional_router.errors.matched_rules_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
