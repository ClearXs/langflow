import subprocess
from datetime import UTC, datetime

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, CodeInput, DataInput, IntInput, MessageTextInput, Output
from lfx.schema import Data


class ETLShellScriptComponent(Component):
    """Shell script execution component with detailed logging."""

    display_name = i18n.t("components.scripts.shell_script.display_name")
    description = i18n.t("components.scripts.shell_script.description")
    icon = "terminal"
    name = "ETLShellScript"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.scripts.shell_script.data_input.display_name"),
            info=i18n.t("components.scripts.shell_script.data_input.info"),
            is_list=True,
        ),
        CodeInput(
            name="script",
            display_name=i18n.t("components.scripts.shell_script.script.display_name"),
            info=i18n.t("components.scripts.shell_script.script.info"),
            required=True,
            value=i18n.t("components.scripts.shell_script.script.default_code"),
            language="bash",
        ),
        BoolInput(
            name="capture_output",
            display_name=i18n.t("components.scripts.shell_script.capture_output.display_name"),
            info=i18n.t("components.scripts.shell_script.capture_output.info"),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.scripts.shell_script.timeout.display_name"),
            info=i18n.t("components.scripts.shell_script.timeout.info"),
            value=30,
            advanced=True,
        ),
        MessageTextInput(
            name="working_directory",
            display_name=i18n.t("components.scripts.shell_script.working_directory.display_name"),
            info=i18n.t("components.scripts.shell_script.working_directory.info"),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.scripts.shell_script.outputs.result.display_name"),
            method="execute_shell",
        )
    ]

    def execute_shell(self) -> Data:
        """Execute Shell script and capture complete log information."""
        start_time = datetime.now(UTC)

        try:
            if not self.script or not self.script.strip():
                no_script_msg = i18n.t("components.scripts.shell_script.errors.no_script")
                # Fallback if i18n key not found
                if "components.scripts" in no_script_msg:
                    no_script_msg = "Script code is required" if i18n.get("locale") == "en" else "脚本代码不能为空"
                raise ValueError(no_script_msg)

            # Execute command
            result = subprocess.run(
                self.script,
                check=False,
                shell=True,  # nosec B602
                capture_output=self.capture_output,
                text=True,
                timeout=self.timeout,
                cwd=self.working_directory if self.working_directory else None,
            )

            # Calculate duration
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Build complete log information in plain text format
            log_lines = [
                f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                if i18n.get("locale") == "zh"
                else f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"执行耗时: {duration:.2f}秒" if i18n.get("locale") == "zh" else f"Duration: {duration:.2f}s",
                f"退出码: {result.returncode}" if i18n.get("locale") == "zh" else f"Exit Code: {result.returncode}",
            ]

            if result.stdout:
                label = "标准输出:" if i18n.get("locale") == "zh" else "Standard Output:"
                log_lines.append(f"\n{label}\n{result.stdout.rstrip()}")

            if result.stderr:
                label = "错误输出:" if i18n.get("locale") == "zh" else "Error Output:"
                log_lines.append(f"\n{label}\n{result.stderr.rstrip()}")

            if result.returncode == 0:
                status_text = "状态: 执行成功" if i18n.get("locale") == "zh" else "Status: Execution Successful"
            else:
                status_text = (
                    f"状态: 执行完成 (退出码: {result.returncode})"
                    if i18n.get("locale") == "zh"
                    else f"Status: Completed (Exit Code: {result.returncode})"
                )
            log_lines.append(f"\n{status_text}")

            # Update status to complete log
            self.status = "\n".join(log_lines)

            # Return data
            output_data = {
                "exit_code": result.returncode,
                "stdout": result.stdout if result.stdout else "",
                "stderr": result.stderr if result.stderr else "",
                "duration": duration,
                "success": result.returncode == 0,
            }

            return Data(data=output_data)

        except subprocess.TimeoutExpired:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Timeout log
            if i18n.get("locale") == "zh":
                timeout_log = "\n".join(
                    [
                        f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"执行耗时: {duration:.2f}秒",
                        f"\n错误: 执行超时 (超过{self.timeout}秒)",
                        "\n状态: 执行失败",
                    ]
                )
            else:
                timeout_log = "\n".join(
                    [
                        f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"Duration: {duration:.2f}s",
                        f"\nError: Execution timeout (exceeded {self.timeout}s)",
                        "\nStatus: Execution Failed",
                    ]
                )

            self.status = timeout_log
            error_msg = i18n.t("components.scripts.shell_script.errors.timeout")
            # Fallback if i18n key not found
            if "components.scripts" in error_msg:
                if i18n.get("locale") == "en":
                    error_msg = f"Execution timeout (exceeded {self.timeout}s)"
                else:
                    error_msg = f"执行超时 (超过{self.timeout}秒)"
            raise ValueError(error_msg) from None

        except Exception as e:
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            # Error log
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
            error_msg = i18n.t("components.scripts.shell_script.errors.execution_failed", error=str(e))
            # Fallback if i18n key not found
            if "components.scripts" in error_msg:
                error_msg = f"Script execution failed: {e!s}" if i18n.get("locale") == "en" else f"脚本执行失败: {e!s}"
            raise ValueError(error_msg) from e
