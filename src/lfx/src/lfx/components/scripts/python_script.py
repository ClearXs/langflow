import sys
from datetime import UTC, datetime
from io import StringIO

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, CodeInput, DataInput, Output
from lfx.schema import Data


class ETLPythonScriptComponent(Component):
    """Python script execution component with detailed logging."""

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
        CodeInput(
            name="script",
            display_name=i18n.t("components.scripts.python_script.script.display_name"),
            info=i18n.t("components.scripts.python_script.script.info"),
            required=True,
            value=i18n.t("components.scripts.python_script.script.default_code"),
        ),
        BoolInput(
            name="capture_output",
            display_name=i18n.t("components.scripts.python_script.capture_output.display_name"),
            info=i18n.t("components.scripts.python_script.capture_output.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.scripts.python_script.outputs.result.display_name"),
            method="execute_python",
        )
    ]

    def execute_python(self) -> Data:
        """Execute Python script and capture complete log information."""
        start_time = datetime.now(UTC)

        try:
            if not self.script or not self.script.strip():
                no_script_msg = i18n.t("components.scripts.python_script.errors.no_script")
                # Fallback if i18n key not found
                if "components.scripts" in no_script_msg:
                    no_script_msg = "Script code is required" if i18n.get("locale") == "en" else "脚本代码不能为空"
                raise ValueError(no_script_msg)

            # Prepare execution environment
            local_vars = {"data_input": self.data_input, "result": None}
            stdout_capture = StringIO() if self.capture_output else None
            stderr_capture = StringIO() if self.capture_output else None

            original_stdout = sys.stdout
            original_stderr = sys.stderr

            try:
                if self.capture_output:
                    sys.stdout = stdout_capture
                    sys.stderr = stderr_capture

                # Execute script
                exec(self.script, {}, local_vars)  # nosec B102

            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr

            # Calculate duration
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Get output
            stdout_text = stdout_capture.getvalue() if stdout_capture else ""
            stderr_text = stderr_capture.getvalue() if stderr_capture else ""
            result_value = local_vars.get("result")

            # Build complete log information in plain text format
            log_lines = [
                f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                if i18n.get("locale") == "zh"
                else f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"执行耗时: {duration:.2f}秒" if i18n.get("locale") == "zh" else f"Duration: {duration:.2f}s",
            ]

            if stdout_text:
                label = "标准输出:" if i18n.get("locale") == "zh" else "Standard Output:"
                log_lines.append(f"\n{label}\n{stdout_text.rstrip()}")

            if stderr_text:
                label = "错误输出:" if i18n.get("locale") == "zh" else "Error Output:"
                log_lines.append(f"\n{label}\n{stderr_text.rstrip()}")

            status_text = "状态: 执行成功" if i18n.get("locale") == "zh" else "Status: Execution Successful"
            log_lines.append(f"\n{status_text}")

            # Update status to complete log
            self.status = "\n".join(log_lines)

            # Return data
            output_data = {
                "result": result_value,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "duration": duration,
                "success": True,
            }

            return Data(data=output_data)

        except Exception as e:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Build error log
            if i18n.get("locale") == "zh":
                error_log = "\n".join(
                    [
                        f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"执行耗时: {duration:.2f}秒",
                        f"\n错误信息: {e!s}",
                        "\n状态: 执行失败",
                    ]
                )
            else:
                error_log = "\n".join(
                    [
                        f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"Duration: {duration:.2f}s",
                        f"\nError: {e!s}",
                        "\nStatus: Execution Failed",
                    ]
                )

            self.status = error_log
            error_msg = i18n.t("components.scripts.python_script.errors.execution_failed", error=str(e))
            # Fallback if i18n key not found
            if "components.scripts" in error_msg:
                error_msg = f"Script execution failed: {e!s}" if i18n.get("locale") == "en" else f"脚本执行失败: {e!s}"
            raise ValueError(error_msg) from e
