"""Transformation executor for applying field transformations."""

from typing import Any

from .builtin import BuiltInTransformations
from .script import ScriptTransformation


class TransformationExecutor:
    """Execute field transformations based on configured rules."""

    def __init__(self):
        """Initialize transformation executor."""
        self.builtin = BuiltInTransformations()
        self.script_engine = ScriptTransformation()

    def transform_row(self, row_data: dict[str, Any], field_mappings: list[dict]) -> dict[str, Any]:
        """Apply transformation rules to entire row data.

        Args:
            row_data: Original row data
            field_mappings: List of field mapping configurations

        Returns:
            Transformed row data
        """
        transformed = {}

        for mapping in field_mappings:
            # Skip disabled mappings
            if not mapping.get("enabled", True):
                continue

            source_field = mapping.get("source_field") or mapping.get("field_name")
            if not source_field:
                continue

            # Get target field name (default to source field)
            target_field = mapping.get("target_field") or mapping.get("field_name") or source_field

            # Get value from source data
            value = row_data.get(source_field)

            # Apply transformation rule
            transformation_rule = mapping.get("transformation_rule")
            if transformation_rule:
                value = self.apply_transformation(value, transformation_rule, row_data)

            # Apply default value if needed
            if value is None or (isinstance(value, str) and value == ""):
                default_value = mapping.get("default_value")
                if default_value is not None:
                    value = default_value

            # Type conversion
            data_type = mapping.get("data_type")
            if data_type:
                value = self.convert_type(value, data_type)

            # Set transformed value
            transformed[target_field] = value

        # Add any unmapped fields from original data
        for key, value in row_data.items():
            if key not in transformed:
                # Check if this field should be included
                mapped_sources = [
                    m.get("source_field") or m.get("field_name") for m in field_mappings if m.get("enabled", True)
                ]
                if not mapped_sources or key in mapped_sources:
                    transformed[key] = value

        return transformed

    def apply_transformation(self, value: Any, rule: str | dict, row_data: dict[str, Any]) -> Any:
        """Apply a single transformation rule.

        Args:
            value: Value to transform
            rule: Transformation rule (string for builtin or dict for complex)
            row_data: Full row data for context

        Returns:
            Transformed value
        """
        if rule is None or rule == "none":
            return value

        # Handle string rule (builtin transformation or expression)
        if isinstance(rule, str):
            # Check if it's a builtin transformation
            if hasattr(self.builtin, rule):
                return getattr(self.builtin, rule)(value)

            # Check if it contains variables or operators (expression)
            if "${" in rule or any(op in rule for op in ["+", "-", "*", "/", ">", "<", "==", "?"]):
                return self.script_engine.apply_expression(value, rule, row_data)

            # Otherwise, treat as simple string replacement
            return rule

        # Handle dict rule (complex transformation)
        if isinstance(rule, dict):
            rule_type = rule.get("type", "builtin")
            rule_content = rule.get("content", rule.get("rule", ""))

            if rule_type == "javascript":
                return self.script_engine.execute_javascript(value, rule_content, row_data)
            if rule_type == "python":
                return self.script_engine.execute_python(value, rule_content, row_data)
            if rule_type == "expression":
                return self.script_engine.apply_expression(value, rule_content, row_data)
            if rule_type == "builtin":
                # Builtin transformation with parameters
                func_name = rule.get("function", rule_content)
                if hasattr(self.builtin, func_name):
                    return getattr(self.builtin, func_name)(value)

        return value

    def convert_type(self, value: Any, data_type: str) -> Any:
        """Convert value to specified data type.

        Args:
            value: Value to convert
            data_type: Target data type

        Returns:
            Converted value
        """
        if value is None:
            return None

        try:
            if data_type == "string" or data_type == "str" or data_type == "text":
                return str(value)
            if data_type == "integer" or data_type == "int":
                return int(float(str(value)))
            if data_type == "float" or data_type == "decimal" or data_type == "number":
                return float(value)
            if data_type == "boolean" or data_type == "bool":
                return self.builtin.to_bool(value)
            if data_type == "json":
                import json

                if isinstance(value, str):
                    return json.loads(value)
                return value
            return value
        except (ValueError, TypeError) as e:
            print(f"Type conversion error: {e}")
            return value
