import os
import i18n
from collections.abc import Callable

from lfx.custom.custom_component.component import Component
from lfx.custom.utils import get_function
from lfx.io import CodeInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict
from lfx.schema.message import Message


class PythonFunctionComponent(Component):
    display_name = i18n.t('components.prototypes.python_function.display_name')
    description = i18n.t('components.prototypes.python_function.description')
    icon = "Python"
    name = "PythonFunction"
    legacy = True

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        CodeInput(
            name="function_code",
            display_name=i18n.t(
                'components.prototypes.python_function.function_code.display_name'),
            info=i18n.t(
                'components.prototypes.python_function.function_code.info'),
        ),
    ]

    outputs = [
        Output(
            name="function_output",
            display_name=i18n.t(
                'components.prototypes.python_function.outputs.function_output.display_name'),
            method="get_function_callable",
        ),
        Output(
            name="function_output_data",
            display_name=i18n.t(
                'components.prototypes.python_function.outputs.function_output_data.display_name'),
            method="execute_function_data",
        ),
        Output(
            name="function_output_str",
            display_name=i18n.t(
                'components.prototypes.python_function.outputs.function_output_str.display_name'),
            method="execute_function_message",
        ),
    ]

    def get_function_callable(self) -> Callable:
        function_code = self.function_code
        self.status = function_code
        return get_function(function_code)

    def execute_function(self) -> list[dotdict | str] | dotdict | str:
        function_code = self.function_code

        if not function_code:
            return "No function code provided."

        try:
            func = get_function(function_code)
            return func()
        except Exception as e:  # noqa: BLE001
            logger.debug("Error executing function", exc_info=True)
            return f"Error executing function: {e}"

    def execute_function_data(self) -> list[Data]:
        results = self.execute_function()
        results = results if isinstance(results, list) else [results]
        return [(Data(text=x) if isinstance(x, str) else Data(**x)) for x in results]

    def execute_function_message(self) -> Message:
        results = self.execute_function()
        results = results if isinstance(results, list) else [results]
        results_list = [str(x) for x in results]
        results_str = "\n".join(results_list)
        return Message(text=results_str)
