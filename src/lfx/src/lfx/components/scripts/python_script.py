import sys
from io import StringIO

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, MultilineInput, Output
from lfx.schema import Data


class ETLPythonScriptComponent(Component):
    display_name = i18n.t("components.scripts.python_script.display_name")
    description = i18n.t("components.scripts.python_script.description")
    icon = "code"
    name = "ETLPythonScript"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.scripts.python_script.data_input.display_name"),
            info=i18n.t("components.scripts.python_script.data_input.info"),
            is_list=True,
        ),
        MultilineInput(
            name="script",
            display_name=i18n.t("components.scripts.python_script.script.display_name"),
            info=i18n.t("components.scripts.python_script.script.info"),
            required=True,
        ),
        BoolInput(
            name="capture_output",
            display_name=i18n.t("components.scripts.python_script.capture_output.display_name"),
            info=i18n.t("components.scripts.python_script.capture_output.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [Output(name="result", display_name="Script Result", method="execute_python")]

    def execute_python(self) -> Data:
        try:
            self.status = i18n.t("components.scripts.python_script.status.executing")
            if not self.script:
                raise ValueError(i18n.t("components.scripts.python_script.errors.no_script"))
            local_vars = {"data_input": self.data_input, "result": None}
            stdout_capture = StringIO() if self.capture_output else None
            stderr_capture = StringIO() if self.capture_output else None
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            try:
                if self.capture_output:
                    sys.stdout = stdout_capture
                    sys.stderr = stderr_capture
                exec(self.script, {}, local_vars)
            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
            output_data = {
                "result": local_vars.get("result"),
                "stdout": stdout_capture.getvalue() if stdout_capture else "",
                "stderr": stderr_capture.getvalue() if stderr_capture else "",
                "success": True,
            }
            self.status = i18n.t("components.scripts.python_script.status.success")
            return Data(data=output_data)
        except Exception as e:
            error_msg = i18n.t("components.scripts.python_script.errors.execution_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
