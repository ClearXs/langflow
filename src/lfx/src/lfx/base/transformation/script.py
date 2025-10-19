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
            python_script = ScriptTransformation._js_to_python(script)

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
                "row": row_data,
            }

            # Execute and return result
            result = eval(python_script, safe_globals, safe_locals)
            return result
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
