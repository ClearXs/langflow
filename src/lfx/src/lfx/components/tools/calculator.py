import ast
import operator
import i18n

import pytest
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import MessageTextInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class CalculatorToolComponent(LCToolComponent):
    display_name = i18n.t('components.tools.calculator.display_name')
    description = i18n.t('components.tools.calculator.description')
    icon = "calculator"
    name = "CalculatorTool"
    legacy = True
    replacement = ["helpers.CalculatorComponent"]

    inputs = [
        MessageTextInput(
            name="expression",
            display_name=i18n.t(
                'components.tools.calculator.expression.display_name'),
            info=i18n.t('components.tools.calculator.expression.info'),
        ),
    ]

    class CalculatorToolSchema(BaseModel):
        expression: str = Field(...,
                                description="The arithmetic expression to evaluate.")

    def run_model(self) -> list[Data]:
        return self._evaluate_expression(self.expression)

    def build_tool(self) -> Tool:
        try:
            from langchain.tools import StructuredTool
        except Exception:  # noqa: BLE001
            pytest.skip("langchain is not available")

        return StructuredTool.from_function(
            name="calculator",
            description=i18n.t('components.tools.calculator.tool_description'),
            func=self._eval_expr_with_error,
            args_schema=self.CalculatorToolSchema,
        )

    def _eval_expr(self, node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            left_val = self._eval_expr(node.left)
            right_val = self._eval_expr(node.right)
            return self.operators[type(node.op)](left_val, right_val)
        if isinstance(node, ast.UnaryOp):
            operand_val = self._eval_expr(node.operand)
            return self.operators[type(node.op)](operand_val)
        if isinstance(node, ast.Call):
            msg = i18n.t(
                'components.tools.calculator.errors.function_calls_not_supported')
            raise TypeError(msg)
        msg = i18n.t('components.tools.calculator.errors.unsupported_operation',
                     operation=type(node).__name__)
        raise TypeError(msg)

    def _eval_expr_with_error(self, expression: str) -> list[Data]:
        try:
            return self._evaluate_expression(expression)
        except Exception as e:
            raise ToolException(str(e)) from e

    def _evaluate_expression(self, expression: str) -> list[Data]:
        try:
            # Parse the expression and evaluate it
            tree = ast.parse(expression, mode="eval")
            result = self._eval_expr(tree.body)

            # Format the result to a reasonable number of decimal places
            formatted_result = f"{result:.6f}".rstrip("0").rstrip(".")

            success_message = i18n.t('components.tools.calculator.success.calculation_completed',
                                     expression=expression, result=formatted_result)
            self.status = success_message
            return [Data(data={"result": formatted_result})]

        except (SyntaxError, TypeError, KeyError) as e:
            error_message = i18n.t(
                'components.tools.calculator.errors.invalid_expression', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message, "input": expression})]
        except ZeroDivisionError:
            error_message = i18n.t(
                'components.tools.calculator.errors.division_by_zero')
            self.status = error_message
            return [Data(data={"error": error_message, "input": expression})]
        except Exception as e:  # noqa: BLE001
            logger.debug("Error evaluating expression", exc_info=True)
            error_message = i18n.t(
                'components.tools.calculator.errors.calculation_error', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message, "input": expression})]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
        }
