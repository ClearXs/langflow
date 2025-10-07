from typing import Any, Dict, List, Union
import re
import json
from datetime import datetime
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
from lfx.schema.message import Message
from lfx.template.field.base import Output


class ConditionalRouterComponent(Component):
    display_name = i18n.t('components.logic.conditional_router.display_name')
    description = i18n.t('components.logic.conditional_router.description')
    documentation: str = "https://docs.langflow.org/components-logic#conditional-router"
    icon = "GitBranch"
    name = "ConditionalRouter"

    inputs = [
        HandleInput(
            name="input_data",
            display_name=i18n.t(
                'components.logic.conditional_router.input_data.display_name'),
            info=i18n.t('components.logic.conditional_router.input_data.info'),
            input_types=["Data", "Message", "Text"],
            required=True,
        ),
        MultilineInput(
            name="conditions",
            display_name=i18n.t(
                'components.logic.conditional_router.conditions.display_name'),
            info=i18n.t('components.logic.conditional_router.conditions.info'),
            placeholder='[\n  {"name": "route1", "condition": "length > 10", "description": "Long text"},\n  {"name": "route2", "condition": "contains(\\"error\\")", "description": "Contains error"}\n]',
            required=True,
        ),
        DropdownInput(
            name="evaluation_mode",
            display_name=i18n.t(
                'components.logic.conditional_router.evaluation_mode.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.evaluation_mode.info'),
            options=["first_match", "all_matches", "best_match"],
            value="first_match",
            advanced=True,
        ),
        MessageTextInput(
            name="default_route",
            display_name=i18n.t(
                'components.logic.conditional_router.default_route.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.default_route.info'),
            value="default",
            advanced=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t(
                'components.logic.conditional_router.case_sensitive.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.case_sensitive.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name=i18n.t(
                'components.logic.conditional_router.include_metadata.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.include_metadata.info'),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="max_routes",
            display_name=i18n.t(
                'components.logic.conditional_router.max_routes.display_name'),
            info=i18n.t('components.logic.conditional_router.max_routes.info'),
            value=0,
            range_spec=(0, 100),
            advanced=True,
        ),
        BoolInput(
            name="strict_mode",
            display_name=i18n.t(
                'components.logic.conditional_router.strict_mode.display_name'),
            info=i18n.t(
                'components.logic.conditional_router.strict_mode.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.logic.conditional_router.text_key.display_name'),
            info=i18n.t('components.logic.conditional_router.text_key.info'),
            value="text",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.conditional_router.outputs.routed_data.display_name'),
            name="routed_data",
            method="route_data",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.conditional_router.outputs.routing_info.display_name'),
            name="routing_info",
            method="get_routing_info",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.conditional_router.outputs.matched_routes.display_name'),
            name="matched_routes",
            method="get_matched_routes",
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "evaluation_mode":
            if field_value == "all_matches":
                build_config["max_routes"]["show"] = True
            else:
                build_config["max_routes"]["show"] = False

        if field_name == "strict_mode":
            if field_value:
                build_config["default_route"]["show"] = False
            else:
                build_config["default_route"]["show"] = True

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        if not self.conditions or not self.conditions.strip():
            error_message = i18n.t(
                'components.logic.conditional_router.errors.empty_conditions')
            self.status = error_message
            raise ValueError(error_message)

        try:
            conditions = json.loads(self.conditions)
            if not isinstance(conditions, list):
                raise ValueError("Conditions must be a list")

            if not conditions:
                raise ValueError("At least one condition is required")

            for i, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    raise ValueError(f"Condition {i} must be an object")

                if "name" not in condition or "condition" not in condition:
                    raise ValueError(
                        f"Condition {i} must have 'name' and 'condition' fields")

        except (json.JSONDecodeError, ValueError) as e:
            error_message = i18n.t('components.logic.conditional_router.errors.invalid_conditions_format',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _get_text_content(self, data: Any) -> str:
        """Extract text content from various data types."""
        if isinstance(data, str):
            return data
        elif isinstance(data, Message):
            return data.text or ""
        elif isinstance(data, Data):
            if hasattr(data, self.text_key):
                return str(getattr(data, self.text_key))
            elif hasattr(data, 'data') and isinstance(data.data, dict):
                return str(data.data.get(self.text_key, data.data.get('text', '')))
            else:
                return str(data)
        elif isinstance(data, dict):
            return str(data.get(self.text_key, data.get('text', '')))
        else:
            return str(data)

    def _evaluate_condition(self, condition_str: str, text: str, data: Any) -> bool:
        """Evaluate a single condition against the data."""
        try:
            # Create evaluation context
            context = {
                'text': text,
                'length': len(text),
                'data': data,
                'now': datetime.now(),
            }

            # Add helper functions
            def contains(substring: str) -> bool:
                if not self.case_sensitive:
                    return substring.lower() in text.lower()
                return substring in text

            def startswith(prefix: str) -> bool:
                if not self.case_sensitive:
                    return text.lower().startswith(prefix.lower())
                return text.startswith(prefix)

            def endswith(suffix: str) -> bool:
                if not self.case_sensitive:
                    return text.lower().endswith(suffix.lower())
                return text.endswith(suffix)

            def matches(pattern: str) -> bool:
                flags = re.IGNORECASE if not self.case_sensitive else 0
                return bool(re.search(pattern, text, flags))

            def count(substring: str) -> int:
                if not self.case_sensitive:
                    return text.lower().count(substring.lower())
                return text.count(substring)

            def is_empty() -> bool:
                return len(text.strip()) == 0

            def is_numeric() -> bool:
                try:
                    float(text)
                    return True
                except ValueError:
                    return False

            def word_count() -> int:
                return len(text.split())

            # Add helper functions to context
            context.update({
                'contains': contains,
                'startswith': startswith,
                'endswith': endswith,
                'matches': matches,
                'count': count,
                'is_empty': is_empty,
                'is_numeric': is_numeric,
                'word_count': word_count,
            })

            # Evaluate the condition
            result = eval(condition_str, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            if self.strict_mode:
                error_message = i18n.t('components.logic.conditional_router.errors.condition_evaluation_error',
                                       condition=condition_str, error=str(e))
                raise ValueError(error_message) from e
            else:
                warning_message = i18n.t('components.logic.conditional_router.warnings.condition_evaluation_warning',
                                         condition=condition_str, error=str(e))
                self.status = warning_message
                return False

    def _evaluate_conditions(self, text: str, data: Any) -> List[Dict[str, Any]]:
        """Evaluate all conditions and return matching ones."""
        try:
            conditions = json.loads(self.conditions)
            matched_conditions = []

            for condition in conditions:
                condition_name = condition.get("name", "unknown")
                condition_str = condition.get("condition", "")
                description = condition.get("description", "")

                try:
                    is_match = self._evaluate_condition(
                        condition_str, text, data)

                    match_info = {
                        "name": condition_name,
                        "condition": condition_str,
                        "description": description,
                        "matched": is_match,
                        "timestamp": datetime.now().isoformat(),
                    }

                    if is_match:
                        matched_conditions.append(match_info)

                    # For first_match mode, return immediately on first match
                    if self.evaluation_mode == "first_match" and is_match:
                        break

                except Exception as e:
                    match_info = {
                        "name": condition_name,
                        "condition": condition_str,
                        "description": description,
                        "matched": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                    if not self.strict_mode:
                        continue
                    else:
                        raise

            # Limit results if max_routes is set
            if self.max_routes > 0 and len(matched_conditions) > self.max_routes:
                matched_conditions = matched_conditions[:self.max_routes]

            return matched_conditions

        except Exception as e:
            error_message = i18n.t('components.logic.conditional_router.errors.conditions_evaluation_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def route_data(self) -> List[Data]:
        """Route data based on conditions."""
        try:
            self._validate_inputs()

            # Extract text content
            text = self._get_text_content(self.input_data)

            # Evaluate conditions
            matched_conditions = self._evaluate_conditions(
                text, self.input_data)

            results = []

            if matched_conditions:
                # Process matched conditions
                for match in matched_conditions:
                    route_data = {
                        "route_name": match["name"],
                        "original_data": self.input_data,
                        "text_content": text,
                        "condition": match["condition"],
                        "description": match.get("description", ""),
                        "matched": True,
                    }

                    if self.include_metadata:
                        route_data["metadata"] = {
                            "evaluation_mode": self.evaluation_mode,
                            "case_sensitive": self.case_sensitive,
                            "timestamp": match["timestamp"],
                            "text_length": len(text),
                        }

                    results.append(
                        Data(data=route_data, text_key="text_content"))

                success_message = i18n.t('components.logic.conditional_router.success.conditions_matched',
                                         count=len(matched_conditions))
                self.status = success_message

            else:
                # No matches - use default route if not in strict mode
                if self.strict_mode:
                    error_message = i18n.t(
                        'components.logic.conditional_router.errors.no_matches_strict_mode')
                    self.status = error_message
                    raise ValueError(error_message)
                else:
                    route_data = {
                        "route_name": self.default_route,
                        "original_data": self.input_data,
                        "text_content": text,
                        "condition": "default",
                        "description": "Default route - no conditions matched",
                        "matched": False,
                    }

                    if self.include_metadata:
                        route_data["metadata"] = {
                            "evaluation_mode": self.evaluation_mode,
                            "case_sensitive": self.case_sensitive,
                            "timestamp": datetime.now().isoformat(),
                            "text_length": len(text),
                        }

                    results.append(
                        Data(data=route_data, text_key="text_content"))

                    warning_message = i18n.t('components.logic.conditional_router.warnings.using_default_route',
                                             route=self.default_route)
                    self.status = warning_message

            return results

        except Exception as e:
            error_message = i18n.t(
                'components.logic.conditional_router.errors.routing_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_routing_info(self) -> Data:
        """Get detailed routing information."""
        try:
            text = self._get_text_content(self.input_data)
            conditions = json.loads(self.conditions)

            routing_info = {
                "input_text_length": len(text),
                "total_conditions": len(conditions),
                "evaluation_mode": self.evaluation_mode,
                "case_sensitive": self.case_sensitive,
                "strict_mode": self.strict_mode,
                "default_route": self.default_route,
                "max_routes": self.max_routes,
                "timestamp": datetime.now().isoformat(),
                "conditions_summary": [
                    {
                        "name": cond.get("name", "unknown"),
                        "description": cond.get("description", ""),
                        "condition": cond.get("condition", "")
                    }
                    for cond in conditions
                ]
            }

            return Data(data=routing_info, text_key="evaluation_mode")

        except Exception as e:
            error_message = i18n.t(
                'components.logic.conditional_router.errors.routing_info_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_matched_routes(self) -> List[Data]:
        """Get list of all matched route names."""
        try:
            text = self._get_text_content(self.input_data)
            matched_conditions = self._evaluate_conditions(
                text, self.input_data)

            if not matched_conditions:
                return [Data(data={"route_name": self.default_route, "is_default": True}, text_key="route_name")]

            results = []
            for match in matched_conditions:
                route_info = {
                    "route_name": match["name"],
                    "description": match.get("description", ""),
                    "condition": match["condition"],
                    "is_default": False,
                }
                results.append(Data(data=route_info, text_key="route_name"))

            return results

        except Exception as e:
            error_message = i18n.t(
                'components.logic.conditional_router.errors.matched_routes_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
