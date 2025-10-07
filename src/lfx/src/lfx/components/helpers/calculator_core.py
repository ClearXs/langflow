import ast
import operator
from collections.abc import Callable
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data


class CalculatorComponent(Component):
    display_name = i18n.t('components.helpers.calculator_core.display_name')
    description = i18n.t('components.helpers.calculator_core.description')
    documentation: str = "https://docs.langflow.org/components-helpers#calculator"
    icon = "calculator"

    # Cache operators dictionary as a class variable
    OPERATORS: dict[type[ast.operator], Callable] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }

    inputs = [
        MessageTextInput(
            name="expression",
            display_name=i18n.t(
                'components.helpers.calculator_core.expression.display_name'),
            info=i18n.t('components.helpers.calculator_core.expression.info'),
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.calculator_core.outputs.result.display_name'),
            name="result",
            type_=Data,
            method="evaluate_expression"
        ),
    ]

    def _eval_expr(self, node: ast.AST) -> float:
        """Evaluate an AST node recursively."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int | float):
                return float(node.value)
            error_msg = i18n.t('components.helpers.calculator_core.errors.unsupported_constant_type',
                               type_name=type(node.value).__name__)
            raise TypeError(error_msg)
        if isinstance(node, ast.Num):  # For backwards compatibility
            if isinstance(node.n, int | float):
                return float(node.n)
            error_msg = i18n.t('components.helpers.calculator_core.errors.unsupported_number_type',
                               type_name=type(node.n).__name__)
            raise TypeError(error_msg)

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                error_msg = i18n.t('components.helpers.calculator_core.errors.unsupported_binary_operator',
                                   operator_name=op_type.__name__)
                raise TypeError(error_msg)

            left = self._eval_expr(node.left)
            right = self._eval_expr(node.right)
            return self.OPERATORS[op_type](left, right)

        error_msg = i18n.t('components.helpers.calculator_core.errors.unsupported_operation',
                           node_type=type(node).__name__)
        raise TypeError(error_msg)

    def evaluate_expression(self) -> Data:
        """Evaluate the mathematical expression and return the result."""
        try:
            if not self.expression or not self.expression.strip():
                error_message = i18n.t(
                    'components.helpers.calculator_core.warnings.empty_expression')
                self.status = error_message
                return Data(data={"error": error_message})

            tree = ast.parse(self.expression, mode="eval")
            result = self._eval_expr(tree.body)

            formatted_result = f"{float(result):.6f}".rstrip("0").rstrip(".")

            log_message = i18n.t('components.helpers.calculator_core.info.calculation_result',
                                 result=formatted_result)
            self.log(log_message)

            self.status = formatted_result
            return Data(data={"result": formatted_result, "expression": self.expression})

        except ZeroDivisionError:
            error_message = i18n.t(
                'components.helpers.calculator_core.errors.division_by_zero')
            self.status = error_message
            return Data(data={"error": error_message, "input": self.expression})

        except SyntaxError as e:
            error_message = i18n.t(
                'components.helpers.calculator_core.errors.syntax_error', error=str(e))
            self.status = error_message
            return Data(data={"error": error_message, "input": self.expression})

        except (TypeError, KeyError, ValueError, AttributeError) as e:
            error_message = i18n.t(
                'components.helpers.calculator_core.errors.invalid_expression', error=str(e))
            self.status = error_message
            return Data(data={"error": error_message, "input": self.expression})

        except OverflowError as e:
            error_message = i18n.t(
                'components.helpers.calculator_core.errors.overflow_error', error=str(e))
            self.status = error_message
            return Data(data={"error": error_message, "input": self.expression})

        except Exception as e:
            error_message = i18n.t(
                'components.helpers.calculator_core.errors.unexpected_error', error=str(e))
            self.status = error_message
            return Data(data={"error": error_message, "input": self.expression})

    def build(self):
        """Return the main evaluation function."""
        return self.evaluate_expression
