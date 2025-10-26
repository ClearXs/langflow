"""Script transformation execution engine."""

import re
from typing import Any


class ScriptTransformation:
    """Execute script-based transformations."""

    @staticmethod
    def execute_javascript(value: Any, script: str, row_data: dict) -> Any:
        """Execute JavaScript transformation script.

        Note: For production use, consider using py_mini_racer or similar.
        This is a simplified implementation using Python eval.
        """
        # For now, we'll use Python eval with JS-like syntax conversion
        # In production, use py_mini_racer or node subprocess
        try:
            # Convert JS-like syntax to Python
            python_script = ScriptTransformation._js_to_python_script(script, row_data)

            # Safe execution environment
            safe_globals = {
                "__builtins__": {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "len": len,
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "round": round,
                }
            }

            safe_locals = {
                "value": value,
                "row": row_data.copy(),  # Make a copy to allow modifications
                "result": row_data.copy() if isinstance(value, dict) else value,
            }

            # Execute script line by line for better handling
            exec(python_script, safe_globals, safe_locals)

            # Return modified row/result
            if "result" in safe_locals and isinstance(safe_locals["result"], dict):
                return safe_locals["result"]
            if "row" in safe_locals and isinstance(safe_locals["row"], dict):
                return safe_locals["row"]
            return safe_locals.get("result", value)
        except Exception as e:
            # Log error and return original value
            print(f"JavaScript execution error: {e}")
            return value

    @staticmethod
    def execute_python(value: Any, script: str, row_data: dict) -> Any:
        """Execute Python transformation script."""
        try:
            # Safe execution environment
            safe_globals = {
                "__builtins__": {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "dict": dict,
                    "list": list,
                    "len": len,
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "round": round,
                    "sum": sum,
                }
            }

            safe_locals = {
                "value": value,
                "row": row_data,
                "result": value,  # Default result
            }

            # Execute script
            exec(script, safe_globals, safe_locals)
            return safe_locals.get("result", value)
        except Exception as e:
            # Log error and return original value
            print(f"Python execution error: {e}")
            return value

    @staticmethod
    def _js_to_python(js_code: str) -> str:
        """Simple JS to Python syntax converter.
        This is a basic implementation for simple expressions.
        """
        # Replace common JS patterns with Python equivalents
        python_code = js_code

        # Ternary operator: condition ? true_val : false_val
        ternary_pattern = r"([^?:]+)\?([^:]+):(.+)"
        if re.match(ternary_pattern, js_code.strip()):
            match = re.match(ternary_pattern, js_code.strip())
            if match:
                condition, true_val, false_val = match.groups()
                python_code = f"({true_val.strip()}) if ({condition.strip()}) else ({false_val.strip()})"

        # Replace === and !== with == and !=
        python_code = python_code.replace("===", "==").replace("!==", "!=")

        # Replace && and || with and/or
        python_code = python_code.replace("&&", " and ").replace("||", " or ")

        # Replace ! with not (careful with !=)
        python_code = re.sub(r"!([^=])", r"not \1", python_code)

        # Replace null with None
        python_code = python_code.replace("null", "None")

        # Replace true/false with True/False
        python_code = python_code.replace("true", "True").replace("false", "False")

        return python_code

    @staticmethod
    def _js_to_python_script(js_code: str, row_data: dict) -> str:
        """Convert JavaScript multi-line script to Python.
        Handles assignments, if statements, and ternary operators.
        """
        lines = js_code.strip().split("\n")
        python_lines = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            # Handle if statements
            if line.startswith("if"):
                # Extract condition and convert
                if_match = re.match(r"if\s*\((.*?)\)\s*\{?", line)
                if if_match:
                    condition = if_match.group(1)
                    # Convert JS condition to Python
                    condition = condition.replace("===", "==").replace("!==", "!=")
                    condition = condition.replace("&&", " and ").replace("||", " or ")
                    condition = re.sub(r"!([^=])", r"not \1", condition)
                    condition = condition.replace("true", "True").replace("false", "False")
                    condition = condition.replace("null", "None")

                    # Handle property access (row.field -> row.get('field'))
                    condition = re.sub(r"row\.(\w+)", r"row.get('\1')", condition)

                    python_lines.append(f"if {condition}:")
                    continue

            # Handle else if
            elif line.startswith("} else if"):
                # Extract condition
                elif_match = re.match(r"\}\s*else\s+if\s*\((.*?)\)\s*\{?", line)
                if elif_match:
                    condition = elif_match.group(1)
                    # Convert JS condition to Python
                    condition = condition.replace("===", "==").replace("!==", "!=")
                    condition = condition.replace("&&", " and ").replace("||", " or ")
                    condition = re.sub(r"!([^=])", r"not \1", condition)
                    condition = condition.replace("true", "True").replace("false", "False")
                    condition = condition.replace("null", "None")

                    # Handle property access
                    condition = re.sub(r"row\.(\w+)", r"row.get('\1')", condition)

                    python_lines.append(f"elif {condition}:")
                    continue

            # Handle else
            elif line.startswith("} else {") or line == "else {":
                python_lines.append("else:")
                continue

            # Skip closing braces
            elif line == "}":
                continue

            # Handle assignments (including ternary operator)
            # Check if it's an assignment
            elif "=" in line and not any(op in line for op in ["==", "!=", ">=", "<="]):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip().rstrip(";")

                    # Convert left side (row.field -> row['field'])
                    if left.startswith("row."):
                        field_name = left[4:]
                        left = f"row['{field_name}']"

                    # Check if right side is a ternary operator
                    ternary_pattern = r"(.*?)\s*\?\s*(.*?)\s*:\s*(.*)"
                    ternary_match = re.match(ternary_pattern, right)

                    if ternary_match:
                        condition, true_val, false_val = ternary_match.groups()
                        # Convert condition
                        condition = condition.replace("===", "==").replace("!==", "!=")
                        condition = condition.replace("&&", " and ").replace("||", " or ")
                        condition = re.sub(r"!([^=])", r"not \1", condition)
                        condition = condition.replace("true", "True").replace("false", "False")
                        condition = condition.replace("null", "None")

                        # Handle property access
                        condition = re.sub(r"row\.(\w+)", r"row.get('\1')", condition)
                        true_val = re.sub(r"row\.(\w+)", r"row.get('\1')", true_val)
                        false_val = re.sub(r"row\.(\w+)", r"row.get('\1')", false_val)

                        # Replace string literals
                        true_val = true_val.replace("'", '"')
                        false_val = false_val.replace("'", '"')

                        right = f"({true_val}) if ({condition}) else ({false_val})"
                    else:
                        # Convert right side
                        right = right.replace("===", "==").replace("!==", "!=")
                        right = right.replace("&&", " and ").replace("||", " or ")
                        right = re.sub(r"!([^=])", r"not \1", right)
                        right = right.replace("true", "True").replace("false", "False")
                        right = right.replace("null", "None")

                        # Handle property access (including chained)
                        right = re.sub(r"row\.(\w+)\.length", r"len(row.get('\1', ''))", right)
                        right = re.sub(r"row\.(\w+)", r"row.get('\1')", right)

                        # Replace string literals
                        right = right.replace("'", '"')

                    python_lines.append(f"    {left} = {right}")

        return "\n".join(python_lines)

    @staticmethod
    def apply_expression(value: Any, expression: str, context: dict) -> Any:
        """Apply expression-based transformation.
        Supports variable substitution with ${variable} syntax.
        """
        try:
            # Replace variables in expression
            def replace_variables(expr: str) -> str:
                pattern = r"\$\{([^}]+)\}"

                def replacer(match):
                    var_path = match.group(1)
                    # Support nested access like ${user.name}
                    result = context
                    for key in var_path.split("."):
                        if isinstance(result, dict) and key in result:
                            result = result[key]
                        else:
                            return str(value)  # Default to current value
                    return str(result)

                return re.sub(pattern, replacer, expr)

            # Process expression
            processed_expr = replace_variables(expression)

            # If it's a simple string replacement, return it
            if "${" not in expression or not any(op in processed_expr for op in ["+", "-", "*", "/", ">", "<", "=="]):
                return processed_expr

            # Otherwise, evaluate as expression
            safe_globals = {
                "__builtins__": {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "len": len,
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "round": round,
                }
            }

            safe_locals = {"value": value}
            safe_locals.update(context)

            result = eval(processed_expr, safe_globals, safe_locals)
            return result
        except Exception as e:
            print(f"Expression evaluation error: {e}")
            return value
