import importlib
import i18n

from langchain_experimental.utilities import PythonREPL

from lfx.custom.custom_component.component import Component
from lfx.io import MultilineInput, Output, StrInput
from lfx.schema.data import Data


class PythonREPLComponent(Component):
    display_name = i18n.t(
        'components.processing.python_repl_core.display_name')
    description = i18n.t('components.processing.python_repl_core.description')
    documentation: str = "https://docs.langflow.org/components-processing#python-interpreter"
    icon = "square-terminal"

    inputs = [
        StrInput(
            name="global_imports",
            display_name=i18n.t(
                'components.processing.python_repl_core.global_imports.display_name'),
            info=i18n.t(
                'components.processing.python_repl_core.global_imports.info'),
            value="math,pandas",
            required=True,
        ),
        MultilineInput(
            name="python_code",
            display_name=i18n.t(
                'components.processing.python_repl_core.python_code.display_name'),
            info=i18n.t(
                'components.processing.python_repl_core.python_code.info'),
            value=i18n.t(
                'components.processing.python_repl_core.python_code.default_value'),
            input_types=["Message"],
            tool_mode=True,
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.python_repl_core.outputs.results.display_name'),
            name="results",
            type_=Data,
            method="run_python_repl",
        ),
    ]

    def get_globals(self, global_imports: str | list[str]) -> dict:
        """Create a globals dictionary with only the specified allowed imports."""
        global_dict = {}

        try:
            # Validate and parse imports
            if isinstance(global_imports, str):
                if not global_imports or not global_imports.strip():
                    warning_msg = i18n.t(
                        'components.processing.python_repl_core.warnings.empty_imports')
                    self.log(warning_msg, "warning")
                    return global_dict
                modules = [module.strip()
                           for module in global_imports.split(",") if module.strip()]
            elif isinstance(global_imports, list):
                modules = [
                    module for module in global_imports if module and isinstance(module, str)]
            else:
                error_msg = i18n.t(
                    'components.processing.python_repl_core.errors.invalid_imports_type')
                self.status = error_msg
                raise TypeError(error_msg)

            if not modules:
                warning_msg = i18n.t(
                    'components.processing.python_repl_core.warnings.no_valid_modules')
                self.log(warning_msg, "warning")
                return global_dict

            # Import modules
            imported_modules = []
            failed_imports = []

            for module in modules:
                try:
                    imported_module = importlib.import_module(module)
                    global_dict[imported_module.__name__] = imported_module
                    imported_modules.append(module)
                except ImportError as e:
                    failed_imports.append((module, str(e)))
                    error_msg = i18n.t('components.processing.python_repl_core.errors.module_import_failed',
                                       module=module, error=str(e))
                    self.log(error_msg, "warning")

            # Report import results
            if imported_modules:
                success_msg = i18n.t('components.processing.python_repl_core.success.modules_imported',
                                     modules=', '.join(imported_modules))
                self.log(success_msg)

            if failed_imports:
                failed_list = [
                    f"{module} ({error})" for module, error in failed_imports]
                warning_msg = i18n.t('components.processing.python_repl_core.warnings.failed_imports',
                                     failures='; '.join(failed_list))
                self.log(warning_msg, "warning")

            return global_dict

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.python_repl_core.errors.global_imports_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise

    def run_python_repl(self) -> Data:
        try:
            # Validate inputs
            if not self.python_code or not self.python_code.strip():
                error_msg = i18n.t(
                    'components.processing.python_repl_core.errors.empty_code')
                self.status = error_msg
                return Data(data={"error": error_msg})

            # Get globals and setup REPL
            self.status = i18n.t(
                'components.processing.python_repl_core.status.preparing_environment')
            globals_ = self.get_globals(self.global_imports)

            self.status = i18n.t(
                'components.processing.python_repl_core.status.executing_code')
            python_repl = PythonREPL(_globals=globals_)

            # Execute code
            result = python_repl.run(self.python_code)
            result = result.strip() if result else ""

            # Handle execution results
            if not result:
                success_msg = i18n.t(
                    'components.processing.python_repl_core.success.code_executed_no_output')
            else:
                success_msg = i18n.t('components.processing.python_repl_core.success.code_executed_with_output',
                                     length=len(result))

            self.status = success_msg
            self.log(success_msg)

            return Data(data={"result": result})

        except ImportError as e:
            error_message = i18n.t(
                'components.processing.python_repl_core.errors.import_error', error=str(e))
            self.status = error_message
            self.log(error_message, "error")
            return Data(data={"error": error_message})

        except SyntaxError as e:
            error_message = i18n.t(
                'components.processing.python_repl_core.errors.syntax_error', error=str(e))
            self.status = error_message
            self.log(error_message, "error")
            return Data(data={"error": error_message})

        except NameError as e:
            error_message = i18n.t(
                'components.processing.python_repl_core.errors.name_error', error=str(e))
            self.status = error_message
            self.log(error_message, "error")
            return Data(data={"error": error_message})

        except (TypeError, ValueError) as e:
            error_message = i18n.t(
                'components.processing.python_repl_core.errors.runtime_error', error=str(e))
            self.status = error_message
            self.log(error_message, "error")
            return Data(data={"error": error_message})

        except Exception as e:
            error_message = i18n.t(
                'components.processing.python_repl_core.errors.execution_failed', error=str(e))
            self.status = error_message
            self.log(error_message, "error")
            return Data(data={"error": error_message})

    def build(self):
        return self.run_python_repl
