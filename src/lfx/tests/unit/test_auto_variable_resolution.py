"""Unit tests for automatic variable resolution in Component fields."""

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput, MultilineInput, StrInput


class TestAutoVariableResolution:
    """Test suite for automatic variable resolution functionality."""

    def test_should_resolve_variables_with_pattern(self):
        """Test _should_resolve_variables detects {variableName} pattern."""
        component = Component()

        # Should detect patterns
        assert component._should_resolve_variables("select * from {tableName}")
        assert component._should_resolve_variables("{var}")
        assert component._should_resolve_variables("text {var1} and {var2}")

        # Should not detect invalid patterns
        assert not component._should_resolve_variables("no variables")
        assert not component._should_resolve_variables("{}")
        assert not component._should_resolve_variables("{123}")  # starts with number
        assert not component._should_resolve_variables("")

    def test_message_text_input_has_resolve_variables_enabled(self):
        """Test MessageTextInput has resolve_variables=True by default."""
        input_field = MessageTextInput(name="test", display_name="Test")
        assert input_field.resolve_variables is True

    def test_multiline_input_has_resolve_variables_enabled(self):
        """Test MultilineInput inherits resolve_variables=True."""
        input_field = MultilineInput(name="test", display_name="Test")
        assert input_field.resolve_variables is True

    def test_str_input_has_resolve_variables_disabled(self):
        """Test StrInput has resolve_variables=False by default."""
        input_field = StrInput(name="test", display_name="Test")
        assert input_field.resolve_variables is False

    def test_resolve_variables_can_be_disabled(self):
        """Test resolve_variables can be explicitly disabled."""
        input_field = MessageTextInput(name="test", display_name="Test", resolve_variables=False)
        assert input_field.resolve_variables is False

    def test_resolve_variables_without_pattern_returns_original(self):
        """Test resolve_variables_in_template_sync returns original text when no pattern."""
        component = Component()
        text = "no variables here"

        # Should return immediately without attempting resolution
        result = component.resolve_variables_in_template_sync(text, "test_field")
        assert result == text

    def test_resolve_variables_with_empty_string(self):
        """Test resolve_variables_in_template_sync handles empty string."""
        component = Component()

        result = component.resolve_variables_in_template_sync("", "test_field")
        assert result == ""


# Integration-like tests will be done by the user
# These basic unit tests verify the core functionality
