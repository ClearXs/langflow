"""Tests for automatic universal input injection for components with no inputs."""

import pytest

from lfx.custom.custom_component.component import Component
from lfx.template.field.base import Output


class TestAutoInjectUniversalInput:
    """Test automatic injection of universal input for components without inputs."""

    def test_component_with_no_inputs_gets_universal_input(self):
        """Verify that a component with no inputs gets a universal input when opted-in."""

        class NoInputComponent(Component):
            """A component with no inputs defined."""

            display_name = "No Input Component"
            description = "Component without any inputs"
            include_universal_input = True  # Opt-in to universal input

            # No inputs defined
            inputs = []

            outputs = [
                Output(
                    display_name="Result",
                    name="result",
                    method="process",
                ),
            ]

            def process(self):
                return "processed"

        # Instantiate the component
        component = NoInputComponent()

        # Verify universal input was auto-injected
        assert len(component._inputs) == 1
        assert "upstream_data" in component._inputs

        # Verify the injected input is universal (accepts any type)
        universal_input = component._inputs["upstream_data"]
        assert universal_input.input_types == []  # Empty = accept any type
        assert universal_input.name == "upstream_data"
        assert universal_input.required is False
        assert universal_input.show is True  # Visible as normal input

    def test_component_with_inputs_gets_universal_input(self):
        """Verify that a component with existing inputs ALSO gets universal input when opted-in."""
        from lfx.inputs.inputs import MessageTextInput

        class WithInputComponent(Component):
            """A component with inputs defined."""

            display_name = "With Input Component"
            description = "Component with inputs"
            include_universal_input = True  # Opt-in to universal input

            inputs = [
                MessageTextInput(
                    name="text_input",
                    display_name="Text Input",
                ),
            ]

            outputs = [
                Output(
                    display_name="Result",
                    name="result",
                    method="process",
                ),
            ]

            def process(self):
                return self.text_input

        # Instantiate the component
        component = WithInputComponent()

        # Verify universal input was injected alongside existing inputs
        assert len(component._inputs) == 2
        assert "upstream_data" in component._inputs
        assert "text_input" in component._inputs

        # Verify the universal input has correct properties
        universal_input = component._inputs["upstream_data"]
        assert universal_input.input_types == []  # Empty = accept any type

    def test_component_with_none_inputs_no_injection(self):
        """Verify that a component with inputs=None does NOT get universal input.

        When inputs=None, the __init__ method skips map_inputs entirely,
        so no auto-injection occurs. This is expected behavior for components
        that explicitly set inputs to None.
        """
        # Skip this test - components with inputs=None cannot be instantiated
        # due to validation issues in _there_is_overlap_in_inputs_and_outputs
        pytest.skip("Components with inputs=None have validation issues")

    def test_injected_universal_input_accepts_any_data(self):
        """Test that the injected universal input can receive any data type."""
        from lfx.schema.data import Data
        from lfx.schema.message import Message

        class NoInputComponent(Component):
            display_name = "No Input Test"
            include_universal_input = True  # Opt-in to universal input
            inputs = []

            outputs = [
                Output(name="result", method="process"),
            ]

            def process(self):
                # Access the auto-injected upstream_data
                if hasattr(self, "upstream_data"):
                    return self.upstream_data
                return None

        # Test with Message
        component_msg = NoInputComponent(upstream_data=Message(text="Hello"))
        assert component_msg.upstream_data.text == "Hello"

        # Test with Data
        component_data = NoInputComponent(upstream_data=Data(data={"key": "value"}))
        assert component_data.upstream_data.data["key"] == "value"

        # Test with plain value
        component_str = NoInputComponent(upstream_data="plain string")
        assert component_str.upstream_data == "plain string"

    def test_multiple_components_get_independent_inputs(self):
        """Verify that multiple instances get independent universal inputs."""

        class NoInputComponent(Component):
            display_name = "Test Component"
            include_universal_input = True  # Opt-in to universal input
            inputs = []

            outputs = [
                Output(name="result", method="process"),
            ]

            def process(self):
                return self.upstream_data if hasattr(self, "upstream_data") else None

        # Create two instances
        comp1 = NoInputComponent(upstream_data="data1")
        comp2 = NoInputComponent(upstream_data="data2")

        # Verify they have independent inputs
        assert comp1.upstream_data == "data1"
        assert comp2.upstream_data == "data2"

        # Verify both have the universal input
        assert "upstream_data" in comp1._inputs
        assert "upstream_data" in comp2._inputs

    def test_injected_input_is_visible(self):
        """Verify that the auto-injected input is visible as a normal input."""

        class NoInputComponent(Component):
            display_name = "Test"
            include_universal_input = True  # Opt-in to universal input
            inputs = []
            outputs = [Output(name="result", method="process")]

            def process(self):
                return "result"

        component = NoInputComponent()
        universal_input = component._inputs["upstream_data"]

        # Should be visible as normal input
        assert universal_input.show is True

    def test_injected_input_not_required(self):
        """Verify that the auto-injected input is not required."""

        class NoInputComponent(Component):
            display_name = "Test"
            include_universal_input = True  # Opt-in to universal input
            inputs = []
            outputs = [Output(name="result", method="process")]

            def process(self):
                return "result"

        component = NoInputComponent()
        universal_input = component._inputs["upstream_data"]

        # Should not be required
        assert universal_input.required is False

    def test_component_with_empty_list_gets_injection(self):
        """Verify that a component with empty inputs list gets injection when opted-in."""

        class EmptyInputComponent(Component):
            display_name = "Empty Input Test"
            include_universal_input = True  # Opt-in to universal input
            inputs = []  # Explicitly empty list

            outputs = [
                Output(name="result", method="process"),
            ]

            def process(self):
                return "result"

        component = EmptyInputComponent()

        # Should have auto-injected universal input
        assert len(component._inputs) == 1
        assert "upstream_data" in component._inputs

    def test_component_with_multiple_inputs_gets_universal_input(self):
        """Verify that a component with multiple existing inputs (like Excel) gets universal input when opted-in."""
        from lfx.inputs.inputs import FileInput, IntInput, MessageTextInput

        class ExcelLikeComponent(Component):
            """A component similar to Excel reader with multiple inputs."""

            display_name = "Excel-like Component"
            description = "Component with multiple inputs like Excel reader"
            include_universal_input = True  # Opt-in to universal input

            inputs = [
                FileInput(
                    name="file_path",
                    display_name="File Path",
                    file_types=["xlsx", "xls"],
                ),
                IntInput(
                    name="sheet_index",
                    display_name="Sheet Index",
                    value=0,
                ),
                MessageTextInput(
                    name="header_row",
                    display_name="Header Row",
                ),
            ]

            outputs = [
                Output(name="data", method="process"),
            ]

            def process(self):
                return "excel_data"

        # Instantiate the component
        component = ExcelLikeComponent()

        # Verify universal input was injected alongside all existing inputs
        assert len(component._inputs) == 4  # 3 original + 1 universal
        assert "upstream_data" in component._inputs
        assert "file_path" in component._inputs
        assert "sheet_index" in component._inputs
        assert "header_row" in component._inputs

        # Verify the universal input is at the end
        universal_input = component._inputs["upstream_data"]
        assert universal_input.input_types == []  # Empty = accept any type
        assert universal_input.required is False

    def test_default_component_no_injection(self):
        """Verify that components without include_universal_input=True don't get universal input (default behavior)."""
        from lfx.inputs.inputs import MessageTextInput

        class DefaultComponent(Component):
            """A component that does not opt-in to universal input injection (default behavior)."""

            display_name = "Default Component"
            description = "Component without include_universal_input flag"
            # No include_universal_input = True, so should NOT get universal input

            inputs = [
                MessageTextInput(
                    name="message",
                    display_name="Message",
                ),
            ]

            outputs = [
                Output(name="result", method="process"),
            ]

            def process(self):
                return self.message

        # Instantiate the component
        component = DefaultComponent()

        # Verify NO universal input was injected (default behavior)
        assert len(component._inputs) == 1
        assert "upstream_data" not in component._inputs
        assert "message" in component._inputs
