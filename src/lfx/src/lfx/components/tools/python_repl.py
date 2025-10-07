import importlib
import i18n

from langchain.tools import StructuredTool
from langchain_core.tools import ToolException
from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class PythonREPLToolComponent(LCToolComponent):
    display_name = i18n.t('components.tools.python_repl.display_name')
    description = i18n.t('components.tools.python_repl.description')
    name = "PythonREPLTool"
    icon = "Python"
    legacy = True
    replacement = ["processing.PythonREPLComponent"]

    inputs = [
        StrInput(
            name="name",
            display_name=i18n.t(
                'components.tools.python_repl.name.display_name'),
            info=i18n.t('components.tools.python_repl.name.info'),
            value="python_repl",
        ),
        StrInput(
            name="description",
            display_name=i18n.t(
                'components.tools.python_repl.tool_description.display_name'),
            info=i18n.t('components.tools.python_repl.tool_description.info'),
            value=i18n.t(
                'components.tools.python_repl.tool_description.default_value'),
        ),
        StrInput(
            name="global_imports",
            display_name=i18n.t(
                'components.tools.python_repl.global_imports.display_name'),
            info=i18n.t('components.tools.python_repl.global_imports.info'),
            value="math",
        ),
        StrInput(
            name="code",
            display_name=i18n.t(
                'components.tools.python_repl.code.display_name'),
            info=i18n.t('components.tools.python_repl.code.info'),
            value="print('Hello, World!')",
        ),
    ]

    class PythonREPLSchema(BaseModel):
        code: str = Field(..., description="The Python code to execute.")

    def get_globals(self, global_imports: str | list[str]) -> dict:
        global_dict = {}

        if isinstance(global_imports, str):
            modules = [module.strip() for module in global_imports.split(",")]
        elif isinstance(global_imports, list):
            modules = global_imports
        else:
            error_message = i18n.t(
                'components.tools.python_repl.errors.invalid_global_imports_type')
            raise TypeError(error_message)

        for module in modules:
            if not module:  # Skip empty module names
                continue

            try:
                imported_module = importlib.import_module(module)
                global_dict[imported_module.__name__] = imported_module
            except ImportError as e:
                error_message = i18n.t('components.tools.python_repl.errors.module_import_failed',
                                       module=module)
                raise ImportError(error_message) from e

        return global_dict

    def build_tool(self) -> Tool:
        try:
            globals_ = self.get_globals(self.global_imports)
            python_repl = PythonREPL(_globals=globals_)

            def run_python_code(code: str) -> str:
                try:
                    if not code or not code.strip():
                        warning_message = i18n.t(
                            'components.tools.python_repl.warnings.empty_code')
                        return warning_message

                    return python_repl.run(code)
                except Exception as e:
                    logger.debug("Error running Python code", exc_info=True)
                    error_message = i18n.t('components.tools.python_repl.errors.code_execution_failed',
                                           error=str(e))
                    raise ToolException(error_message) from e

            tool = StructuredTool.from_function(
                name=self.name,
                description=self.description,
                func=run_python_code,
                args_schema=self.PythonREPLSchema,
            )

            success_message = i18n.t('components.tools.python_repl.success.tool_created',
                                     imports=self.global_imports)
            self.status = success_message
            return tool

        except Exception as e:
            error_message = i18n.t('components.tools.python_repl.errors.tool_creation_failed',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def run_model(self) -> list[Data]:
        try:
            if not self.code or not self.code.strip():
                warning_message = i18n.t(
                    'components.tools.python_repl.warnings.empty_code')
                self.status = warning_message
                return [Data(data={"error": warning_message, "code": self.code})]

            executing_message = i18n.t(
                'components.tools.python_repl.info.executing_code')
            self.status = executing_message

            tool = self.build_tool()
            result = tool.run(self.code)

            success_message = i18n.t(
                'components.tools.python_repl.success.code_executed')
            self.status = success_message

            return [Data(data={"result": result, "code": self.code})]

        except ToolException as e:
            # ToolException is already formatted with i18n message
            error_message = str(e)
            self.status = error_message
            return [Data(data={"error": error_message, "code": self.code})]
        except Exception as e:
            error_message = i18n.t('components.tools.python_repl.errors.execution_failed',
                                   error=str(e))
            self.status = error_message
            logger.debug("Error in run_model", exc_info=True)
            return [Data(data={"error": error_message, "code": self.code})]
