"""Tests for flexible input types with optional upstream connections."""


from lfx.inputs.inputs import (
    DataFrameInput,
    DataInput,
    DropdownInput,
    FloatInput,
    IntInput,
    MessageInput,
    MessageTextInput,
    SecretStrInput,
)


class TestFlexibleInputDefaults:
    """Test that default behavior is preserved for all input types."""

    def test_message_text_input_default_unchanged(self):
        """Verify MessageTextInput uses default ['Message'] when input_types not specified."""
        msg_input = MessageTextInput(name="test_text")
        assert msg_input.input_types == ["Message"]
        assert msg_input.name == "test_text"

    def test_message_input_default_unchanged(self):
        """Verify MessageInput uses default ['Message'] when input_types not specified."""
        msg_input = MessageInput(name="test_message")
        assert msg_input.input_types == ["Message"]

    def test_data_input_default_unchanged(self):
        """Verify DataInput uses default ['Data'] when input_types not specified."""
        data_input = DataInput(name="test_data")
        assert data_input.input_types == ["Data"]

    def test_dataframe_input_default_unchanged(self):
        """Verify DataFrameInput uses default ['DataFrame'] when input_types not specified."""
        df_input = DataFrameInput(name="test_df")
        assert df_input.input_types == ["DataFrame"]

    def test_secret_str_input_default_unchanged(self):
        """Verify SecretStrInput uses default [] (no upstream) when input_types not specified."""
        secret_input = SecretStrInput(name="test_secret")
        assert secret_input.input_types == []

    def test_int_input_default_no_upstream(self):
        """Verify IntInput defaults to None (no upstream connection)."""
        int_input = IntInput(name="test_int", value=10)
        assert int_input.input_types is None

    def test_float_input_default_no_upstream(self):
        """Verify FloatInput defaults to None (no upstream connection)."""
        float_input = FloatInput(name="test_float", value=0.5)
        assert float_input.input_types is None

    def test_dropdown_input_default_no_upstream(self):
        """Verify DropdownInput defaults to None (no upstream connection)."""
        dropdown = DropdownInput(
            name="test_dropdown",
            options=["option1", "option2"],
            value="option1",
        )
        assert dropdown.input_types is None


class TestFlexibleInputOverrides:
    """Test that input_types can be overridden for flexible upstream connections."""

    def test_message_text_input_accept_any(self):
        """Verify MessageTextInput can accept any type with input_types=[]."""
        msg_input = MessageTextInput(name="test_text", input_types=[])
        assert msg_input.input_types == []

    def test_message_text_input_specific_types(self):
        """Verify MessageTextInput can accept specific types."""
        msg_input = MessageTextInput(
            name="test_text",
            input_types=["Data", "Message"],
        )
        assert msg_input.input_types == ["Data", "Message"]

    def test_message_input_accept_any(self):
        """Verify MessageInput can accept any type with input_types=[]."""
        msg_input = MessageInput(name="test_message", input_types=[])
        assert msg_input.input_types == []

    def test_data_input_accept_any(self):
        """Verify DataInput can accept any type with input_types=[]."""
        data_input = DataInput(name="test_data", input_types=[])
        assert data_input.input_types == []

    def test_data_input_specific_types(self):
        """Verify DataInput can accept specific types."""
        data_input = DataInput(
            name="test_data",
            input_types=["Data", "Message"],
        )
        assert data_input.input_types == ["Data", "Message"]

    def test_dataframe_input_accept_any(self):
        """Verify DataFrameInput can accept any type with input_types=[]."""
        df_input = DataFrameInput(name="test_df", input_types=[])
        assert df_input.input_types == []

    def test_secret_str_input_override_with_caution(self):
        """Verify SecretStrInput can be overridden (but should be used with caution)."""
        # This should work but is not recommended for security
        secret_input = SecretStrInput(name="test_secret", input_types=["Data"])
        assert secret_input.input_types == ["Data"]

    def test_int_input_enable_upstream_any(self):
        """Verify IntInput can accept any type when input_types=[]."""
        int_input = IntInput(name="test_int", value=10, input_types=[])
        assert int_input.input_types == []

    def test_int_input_enable_upstream_specific(self):
        """Verify IntInput can accept specific types."""
        int_input = IntInput(
            name="test_int",
            value=10,
            input_types=["Data"],
        )
        assert int_input.input_types == ["Data"]

    def test_float_input_enable_upstream(self):
        """Verify FloatInput can be configured to accept upstream."""
        float_input = FloatInput(
            name="test_float",
            value=0.7,
            input_types=["Data", "Message"],
        )
        assert float_input.input_types == ["Data", "Message"]

    def test_dropdown_input_enable_upstream(self):
        """Verify DropdownInput can be configured to accept upstream."""
        dropdown = DropdownInput(
            name="test_dropdown",
            options=["gpt-4", "gpt-3.5"],
            value="gpt-4",
            input_types=["Data"],
        )
        assert dropdown.input_types == ["Data"]


class TestHelperMethods:
    """Test the enable_upstream_connection and disable_upstream_connection helper methods."""

    def test_enable_upstream_any(self):
        """Test enable_upstream_connection with 'any' parameter."""
        int_input = IntInput(name="test", value=10)
        result = int_input.enable_upstream_connection("any")

        assert int_input.input_types == []
        assert result is int_input  # Method chaining

    def test_enable_upstream_default(self):
        """Test enable_upstream_connection with None (default common types)."""
        float_input = FloatInput(name="test", value=0.5)
        result = float_input.enable_upstream_connection()

        assert float_input.input_types == ["Data", "Message"]
        assert result is float_input

    def test_enable_upstream_specific_list(self):
        """Test enable_upstream_connection with specific type list."""
        dropdown = DropdownInput(
            name="test",
            options=["a", "b"],
            value="a",
        )
        result = dropdown.enable_upstream_connection(["Data", "Message"])

        assert dropdown.input_types == ["Data", "Message"]
        assert result is dropdown

    def test_enable_upstream_single_string(self):
        """Test enable_upstream_connection with single type as string."""
        int_input = IntInput(name="test", value=10)
        result = int_input.enable_upstream_connection("Data")

        assert int_input.input_types == ["Data"]
        assert result is int_input

    def test_disable_upstream(self):
        """Test disable_upstream_connection method."""
        # For IntInput (supports None), disabling should set to None
        int_input = IntInput(name="test", value=10, input_types=[])
        assert int_input.input_types == []

        result = int_input.disable_upstream_connection()

        assert int_input.input_types is None
        assert result is int_input

    def test_disable_upstream_for_message_text_input(self):
        """Test disable_upstream_connection for fields that don't support None."""
        # MessageTextInput has input_types: list[str] (not nullable)
        # So disable_upstream_connection will silently do nothing
        msg_input = MessageTextInput(name="test", input_types=[])
        assert msg_input.input_types == []

        # This will not change the value (silent no-op)
        result = msg_input.disable_upstream_connection()

        # input_types remains unchanged because Pydantic won't allow None
        assert msg_input.input_types == []  # Still empty list
        assert result is msg_input  # Method chaining still works

    def test_method_chaining(self):
        """Test that helper methods support chaining."""
        int_input = IntInput(name="test", value=10)

        # Chain multiple operations
        int_input.enable_upstream_connection("any").disable_upstream_connection().enable_upstream_connection(["Data"])

        assert int_input.input_types == ["Data"]


class TestBackwardCompatibility:
    """Test that existing code patterns continue to work."""

    def test_existing_usage_without_input_types(self):
        """Verify existing code that doesn't pass input_types still works."""
        # This is how 99% of existing components are defined
        msg_input = MessageTextInput(
            name="text",
            display_name="Input Text",
            info="Enter your text",
            required=True,
        )

        assert msg_input.input_types == ["Message"]
        assert msg_input.name == "text"
        assert msg_input.display_name == "Input Text"
        assert msg_input.required is True

    def test_existing_usage_with_other_params(self):
        """Verify existing code with various parameters still works."""
        data_input = DataInput(
            name="data",
            display_name="Data Input",
            info="Input data",
            is_list=True,
            required=False,
        )

        assert data_input.input_types == ["Data"]
        assert data_input.is_list is True
        assert data_input.required is False

    def test_dropdown_with_options(self):
        """Verify DropdownInput with options still works."""
        dropdown = DropdownInput(
            name="model",
            display_name="Model",
            options=["gpt-4", "gpt-3.5-turbo", "claude-3"],
            value="gpt-4",
            info="Select model",
        )

        assert dropdown.input_types is None  # Default for DropdownInput
        assert dropdown.options == ["gpt-4", "gpt-3.5-turbo", "claude-3"]
        assert dropdown.value == "gpt-4"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_list_vs_none(self):
        """Verify difference between [] (accept any) and None (no upstream)."""
        # Empty list = accept any type
        input_any = IntInput(name="test1", value=10, input_types=[])
        assert input_any.input_types == []

        # None = no upstream connection
        input_none = IntInput(name="test2", value=10, input_types=None)
        assert input_none.input_types is None

        # Not specified = use default (None for IntInput)
        input_default = IntInput(name="test3", value=10)
        assert input_default.input_types is None

    def test_single_type_list(self):
        """Verify single-type list works correctly."""
        data_input = DataInput(name="test", input_types=["Message"])
        assert data_input.input_types == ["Message"]
        assert len(data_input.input_types) == 1

    def test_multiple_types_list(self):
        """Verify multiple types can be specified."""
        msg_input = MessageTextInput(
            name="test",
            input_types=["Message", "Data", "str"],
        )
        assert msg_input.input_types == ["Message", "Data", "str"]
        assert len(msg_input.input_types) == 3

    def test_override_to_different_type(self):
        """Verify default type can be completely overridden."""
        # MessageTextInput default is ["Message"]
        # Override to accept only Data
        msg_input = MessageTextInput(name="test", input_types=["Data"])
        assert msg_input.input_types == ["Data"]
        assert "Message" not in msg_input.input_types
