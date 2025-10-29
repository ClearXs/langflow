"""Unit tests for Shell Script component."""

import pytest

from lfx.components.scripts.shell_script import ETLShellScriptComponent
from lfx.schema import Data


class TestShellScriptComponent:
    """测试Shell脚本组件"""

    def test_basic_execution(self):
        """测试基本Shell命令执行和日志格式"""
        component = ETLShellScriptComponent(script="echo 'test'", data_input=[], capture_output=True)
        output = component.execute_shell()

        # 验证数据输出
        assert output.data["exit_code"] == 0
        assert output.data["success"] is True
        assert "test" in output.data["stdout"]
        assert "duration" in output.data

        # 验证日志格式（纯文本，无emoji）
        assert component.status is not None
        assert "开始时间:" in component.status or "Start Time:" in component.status
        assert "执行耗时:" in component.status or "Duration:" in component.status
        assert "退出码:" in component.status or "Exit Code:" in component.status
        assert "状态:" in component.status or "Status:" in component.status

    def test_stdout_capture(self):
        """测试标准输出捕获"""
        component = ETLShellScriptComponent(
            script="echo 'Hello World'\necho 'Line 2'",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_shell()

        assert "Hello World" in output.data["stdout"]
        assert "Line 2" in output.data["stdout"]
        assert output.data["exit_code"] == 0
        # 日志中应包含stdout内容
        assert "Hello World" in component.status

    def test_stderr_capture(self):
        """测试错误输出捕获"""
        component = ETLShellScriptComponent(
            script="echo 'Warning message' >&2",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_shell()

        assert "Warning message" in output.data["stderr"]
        assert output.data["exit_code"] == 0
        # 日志中应包含stderr标记
        assert "错误输出:" in component.status or "Error Output:" in component.status

    def test_exit_code_success(self):
        """测试成功的退出码"""
        component = ETLShellScriptComponent(script="exit 0", data_input=[], capture_output=True)
        output = component.execute_shell()

        assert output.data["exit_code"] == 0
        assert output.data["success"] is True
        assert "状态: 执行成功" in component.status or "Status: Execution Successful" in component.status

    def test_exit_code_failure(self):
        """测试失败的退出码"""
        component = ETLShellScriptComponent(script="exit 1", data_input=[], capture_output=True)
        output = component.execute_shell()

        assert output.data["exit_code"] == 1
        assert output.data["success"] is False
        # 应该有完成状态，但不是成功
        assert "退出码: 1" in component.status or "Exit Code: 1" in component.status

    def test_empty_script(self):
        """测试空脚本"""
        component = ETLShellScriptComponent(script="", data_input=[], capture_output=True)

        with pytest.raises(ValueError) as exc_info:
            component.execute_shell()

        error_msg = str(exc_info.value).lower()
        assert "required" in error_msg or "empty" in error_msg or "不能为空" in str(exc_info.value)

    def test_multiline_commands(self):
        """测试多行命令"""
        script = """
echo 'Line 1'
echo 'Line 2'
echo 'Line 3'
"""
        component = ETLShellScriptComponent(script=script, data_input=[], capture_output=True)
        output = component.execute_shell()

        assert output.data["exit_code"] == 0
        assert "Line 1" in output.data["stdout"]
        assert "Line 2" in output.data["stdout"]
        assert "Line 3" in output.data["stdout"]

    def test_working_directory(self):
        """测试工作目录设置"""
        component = ETLShellScriptComponent(
            script="pwd",
            data_input=[],
            capture_output=True,
            working_directory="/tmp",
        )
        output = component.execute_shell()

        assert output.data["exit_code"] == 0
        assert "/tmp" in output.data["stdout"]

    def test_timeout_error(self):
        """测试超时错误处理"""
        component = ETLShellScriptComponent(
            script="sleep 10",  # Sleep for 10 seconds
            data_input=[],
            capture_output=True,
            timeout=1,  # But timeout after 1 second
        )

        with pytest.raises(ValueError) as exc_info:
            component.execute_shell()

        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "超时" in str(exc_info.value)

        # 验证超时日志
        assert component.status is not None
        assert "错误:" in component.status or "Error:" in component.status
        assert "状态: 执行失败" in component.status or "Status: Execution Failed" in component.status

    def test_output_without_capture(self):
        """测试不捕获输出的情况"""
        component = ETLShellScriptComponent(
            script="echo 'This should not be captured'",
            data_input=[],
            capture_output=False,
        )
        output = component.execute_shell()

        assert output.data["exit_code"] == 0
        assert output.data["stdout"] == ""
        assert output.data["stderr"] == ""
        assert output.data["success"] is True

    def test_duration_measurement(self):
        """测试执行时间测量"""
        component = ETLShellScriptComponent(
            script="sleep 0.1",  # Sleep for 0.1 seconds
            data_input=[],
            capture_output=True,
        )
        output = component.execute_shell()

        # 耗时应该大于等于0.1秒
        assert output.data["duration"] >= 0.1
        assert "执行耗时:" in component.status or "Duration:" in component.status

    def test_command_with_pipes(self):
        """测试带管道的命令"""
        component = ETLShellScriptComponent(
            script="echo 'hello world' | tr 'a-z' 'A-Z'",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_shell()

        assert output.data["exit_code"] == 0
        assert "HELLO WORLD" in output.data["stdout"]

    def test_data_input_passthrough(self):
        """测试数据输入透传（Shell脚本不直接使用data_input，但应该接受）"""
        data = [Data(data={"id": 1}), Data(data={"id": 2})]
        component = ETLShellScriptComponent(script="echo 'test'", data_input=data, capture_output=True)
        output = component.execute_shell()

        # 应该正常执行，data_input被接受但不影响脚本执行
        assert output.data["exit_code"] == 0
        assert output.data["success"] is True
