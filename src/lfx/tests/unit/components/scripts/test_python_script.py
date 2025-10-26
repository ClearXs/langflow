"""Unit tests for Python Script component."""

import pytest

from lfx.components.scripts.python_script import ETLPythonScriptComponent
from lfx.schema import Data


class TestPythonScriptComponent:
    """测试Python脚本组件"""

    def test_basic_execution(self):
        """测试基本代码执行和日志格式"""
        component = ETLPythonScriptComponent(
            script="print('test')\nresult = 42", data_input=[], capture_output=True
        )
        output = component.execute_python()

        # 验证数据输出
        assert output.data["result"] == 42
        assert output.data["success"] is True
        assert "test" in output.data["stdout"]
        assert "duration" in output.data

        # 验证日志格式（纯文本，无emoji）
        assert component.status is not None
        assert (
            "开始时间:" in component.status or "Start Time:" in component.status
        )
        assert "执行耗时:" in component.status or "Duration:" in component.status
        assert "标准输出:" in component.status or "Standard Output:" in component.status
        assert "test" in component.status
        assert "状态:" in component.status or "Status:" in component.status

    def test_data_input_access(self):
        """测试访问上游数据"""
        data = [Data(data={"id": 1}), Data(data={"id": 2})]
        component = ETLPythonScriptComponent(
            script="result = [item.data['id'] for item in data_input]",
            data_input=data,
            capture_output=True,
        )
        output = component.execute_python()

        assert output.data["result"] == [1, 2]
        assert output.data["success"] is True

    def test_stdout_capture(self):
        """测试标准输出捕获"""
        component = ETLPythonScriptComponent(
            script="print('Hello World')\nprint('Line 2')\nresult = 'done'",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_python()

        assert "Hello World" in output.data["stdout"]
        assert "Line 2" in output.data["stdout"]
        assert output.data["result"] == "done"
        # 日志中应包含stdout内容
        assert "Hello World" in component.status

    def test_stderr_capture(self):
        """测试错误输出捕获"""
        component = ETLPythonScriptComponent(
            script="import sys\nsys.stderr.write('Warning message\\n')\nresult = 'done'",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_python()

        assert "Warning message" in output.data["stderr"]
        assert output.data["result"] == "done"
        # 日志中应包含stderr标记
        assert "错误输出:" in component.status or "Error Output:" in component.status

    def test_error_handling(self):
        """测试错误处理和错误日志"""
        component = ETLPythonScriptComponent(
            script="result = undefined_variable", data_input=[], capture_output=True
        )

        with pytest.raises(ValueError) as exc_info:
            component.execute_python()

        assert "execution failed" in str(exc_info.value).lower() or "执行失败" in str(
            exc_info.value
        )

        # 验证错误日志
        assert component.status is not None
        assert "错误信息:" in component.status or "Error:" in component.status
        assert (
            "状态: 执行失败" in component.status
            or "Status: Execution Failed" in component.status
        )

    def test_empty_script(self):
        """测试空脚本"""
        component = ETLPythonScriptComponent(
            script="", data_input=[], capture_output=True
        )

        with pytest.raises(ValueError) as exc_info:
            component.execute_python()

        error_msg = str(exc_info.value).lower()
        assert (
            "required" in error_msg
            or "empty" in error_msg
            or "不能为空" in str(exc_info.value)
        )

    def test_complex_data_processing(self):
        """测试复杂数据处理"""
        data = [
            Data(data={"name": "Alice", "age": 30}),
            Data(data={"name": "Bob", "age": 25}),
            Data(data={"name": "Charlie", "age": 35}),
        ]

        script = """
processed = []
for item in data_input:
    d = item.data
    d['age_group'] = 'adult' if d['age'] >= 30 else 'young'
    processed.append(d)

result = {
    'total': len(processed),
    'data': processed
}
"""

        component = ETLPythonScriptComponent(
            script=script, data_input=data, capture_output=True
        )
        output = component.execute_python()

        assert output.data["result"]["total"] == 3
        assert output.data["success"] is True
        assert output.data["result"]["data"][0]["age_group"] == "adult"
        assert output.data["result"]["data"][1]["age_group"] == "young"

    def test_output_without_capture(self):
        """测试不捕获输出的情况"""
        component = ETLPythonScriptComponent(
            script="print('This should not be captured')\nresult = 42",
            data_input=[],
            capture_output=False,
        )
        output = component.execute_python()

        assert output.data["result"] == 42
        assert output.data["stdout"] == ""
        assert output.data["stderr"] == ""
        assert output.data["success"] is True

    def test_duration_measurement(self):
        """测试执行时间测量"""
        component = ETLPythonScriptComponent(
            script="import time\ntime.sleep(0.1)\nresult = 'done'",
            data_input=[],
            capture_output=True,
        )
        output = component.execute_python()

        # 耗时应该大于0.1秒
        assert output.data["duration"] >= 0.1
        assert "执行耗时:" in component.status or "Duration:" in component.status
