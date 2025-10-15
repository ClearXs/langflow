from typing import Any
import i18n
import subprocess
import shlex

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MultilineInput, MessageTextInput, IntInput, BoolInput, Output
from lfx.schema import Data


class ETLShellScriptComponent(Component):
    display_name = i18n.t('components.scripts.shell_script.display_name')
    description = i18n.t('components.scripts.shell_script.description')
    icon = "terminal"
    name = "ETLShellScript"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.scripts.shell_script.data_input.display_name'), info=i18n.t('components.scripts.shell_script.data_input.info'), is_list=True),
        MultilineInput(name="script", display_name=i18n.t('components.scripts.shell_script.script.display_name'), info=i18n.t('components.scripts.shell_script.script.info'), required=True),
        MessageTextInput(name="working_directory", display_name=i18n.t('components.scripts.shell_script.working_directory.display_name'), info=i18n.t('components.scripts.shell_script.working_directory.info'), advanced=True),
        IntInput(name="timeout", display_name=i18n.t('components.scripts.shell_script.timeout.display_name'), info=i18n.t('components.scripts.shell_script.timeout.info'), value=300, advanced=True),
        BoolInput(name="capture_output", display_name=i18n.t('components.scripts.shell_script.capture_output.display_name'), info=i18n.t('components.scripts.shell_script.capture_output.info'), value=True, advanced=True)
    ]

    outputs = [Output(name="result", display_name="Script Result", method="execute_shell")]

    def execute_shell(self) -> Data:
        try:
            self.status = i18n.t('components.scripts.shell_script.status.executing')
            if not self.script:
                raise ValueError(i18n.t('components.scripts.shell_script.errors.no_script'))
            result = subprocess.run(self.script, shell=True, capture_output=self.capture_output, text=True, timeout=self.timeout, cwd=self.working_directory if self.working_directory else None)
            output_data = {"exit_code": result.returncode, "stdout": result.stdout if self.capture_output else "", "stderr": result.stderr if self.capture_output else "", "success": result.returncode == 0}
            self.status = i18n.t('components.scripts.shell_script.status.success', code=result.returncode)
            return Data(data=output_data)
        except subprocess.TimeoutExpired:
            error_msg = i18n.t('components.scripts.shell_script.errors.timeout')
            self.status = error_msg
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = i18n.t('components.scripts.shell_script.errors.execution_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
