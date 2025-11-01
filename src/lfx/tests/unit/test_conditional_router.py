"""Unit tests for ConditionalRouterComponent."""

from unittest.mock import patch

from lfx.components.logic.conditional_router import ConditionalRouterComponent
from lfx.schema import Data, Message


class TestConditionalRouterComponent:
    """Test suite for Conditional Router component."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock translation function
        self.mock_i18n = patch("i18n.t", side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key)
        self.mock_i18n.start()

    def teardown_method(self):
        """Clean up after tests."""
        self.mock_i18n.stop()

    # ==================== Test Group 1: Component Initialization ====================

    def test_component_initialization(self):
        """Test component initializes correctly."""
        component = ConditionalRouterComponent()

        assert component.display_name is not None
        assert component.icon == "split"
        assert component.name == "ConditionalRouter"
        assert len(component.inputs) > 0
        assert len(component.outputs) == 2  # true_result and false_result

        # Check for caching attributes
        assert hasattr(component, "_field_cache")
        assert hasattr(component, "_cache_ttl")
        assert hasattr(component, "_field_info_cache")

    # ==================== Test Group 2: Field Type Inference ====================

    def test_infer_string_type(self):
        """Test field type inference for string values."""
        component = ConditionalRouterComponent()

        # Test with string values
        field_type = component.infer_field_type("name", ["Alice", "Bob", "Charlie"])
        assert field_type == "string"

        # Test with mixed strings and numbers (should default to string)
        field_type = component.infer_field_type("mixed", ["Alice", "123", "Bob"])
        assert field_type == "string"

    def test_infer_numeric_type(self):
        """Test field type inference for numeric values."""
        component = ConditionalRouterComponent()

        # Test with integers
        field_type = component.infer_field_type("age", [25, 30, 35])
        assert field_type == "number"

        # Test with floats
        field_type = component.infer_field_type("price", [10.99, 25.50, 100.00])
        assert field_type == "number"

        # Test with numeric strings
        field_type = component.infer_field_type("score", ["85", "92", "78"])
        assert field_type == "number"

    def test_infer_boolean_type(self):
        """Test field type inference for boolean values."""
        component = ConditionalRouterComponent()

        # Test with boolean values
        field_type = component.infer_field_type("active", [True, False, True])
        assert field_type == "boolean"

        # Test with boolean strings
        field_type = component.infer_field_type("enabled", ["true", "false", "yes"])
        assert field_type == "boolean"

    def test_infer_date_type(self):
        """Test field type inference for date values."""
        component = ConditionalRouterComponent()

        # Test with different date formats
        field_type = component.infer_field_type("created", ["2024-01-15", "2024-02-20", "2024-03-10"])
        assert field_type == "date"

        field_type = component.infer_field_type("date", ["01/15/2024", "02/20/2024"])
        assert field_type == "date"

    def test_infer_type_with_empty_values(self):
        """Test field type inference with empty or null values."""
        component = ConditionalRouterComponent()

        # Test with empty list
        field_type = component.infer_field_type("empty", [])
        assert field_type == "string"

        # Test with None values
        field_type = component.infer_field_type("nulls", [None, None, None])
        assert field_type == "string"

    # ==================== Test Group 3: Field Value Extraction ====================

    def test_extract_field_value_from_dict(self):
        """Test field extraction from dictionary."""
        component = ConditionalRouterComponent()
        data = {"name": "Alice", "age": 30, "profile": {"email": "alice@example.com"}}

        # Test simple field
        value = component.extract_field_value(data, "name")
        assert value == "Alice"

        # Test nested field
        value = component.extract_field_value(data, "profile.email")
        assert value == "alice@example.com"

    def test_extract_field_value_from_data_object(self):
        """Test field extraction from Data object."""
        component = ConditionalRouterComponent()
        data = Data(data={"name": "Alice", "age": 30})

        value = component.extract_field_value(data, "name")
        assert value == "Alice"

    def test_extract_field_value_from_message(self):
        """Test field extraction from Message object."""
        component = ConditionalRouterComponent()
        message = Message(text="Hello World", data={"user": "Alice"})

        # Test extraction from data
        value = component.extract_field_value(message, "user")
        assert value == "Alice"

        # Test fallback to text
        value = component.extract_field_value(message, "text")
        assert value == "Hello World"

    def test_extract_field_value_not_found(self):
        """Test field extraction when field doesn't exist."""
        component = ConditionalRouterComponent()
        data = {"name": "Alice"}

        value = component.extract_field_value(data, "nonexistent")
        assert value == ""

    # ==================== Test Group 4: Condition Evaluation ====================

    def test_evaluate_condition_equals(self):
        """Test equals operator."""
        component = ConditionalRouterComponent()

        result = component.evaluate_condition("Alice", "Alice", "equals", case_sensitive=True)
        assert result is True

        result = component.evaluate_condition("Alice", "Bob", "equals", case_sensitive=True)
        assert result is False

    def test_evaluate_condition_contains(self):
        """Test contains operator."""
        component = ConditionalRouterComponent()

        result = component.evaluate_condition("Hello World", "World", "contains", case_sensitive=True)
        assert result is True

        result = component.evaluate_condition("Hello World", "world", "contains", case_sensitive=False)
        assert result is True

    def test_evaluate_condition_numeric(self):
        """Test numeric comparison operators."""
        component = ConditionalRouterComponent()

        # Test greater than
        result = component.evaluate_condition("25", "20", "greater than", case_sensitive=True)
        assert result is True

        # Test less than or equal
        result = component.evaluate_condition("20", "20", "less than or equal", case_sensitive=True)
        assert result is True

    def test_evaluate_condition_regex(self):
        """Test regex operator."""
        component = ConditionalRouterComponent()

        result = component.evaluate_condition("abc123", r"[a-z]+\d+", "regex", case_sensitive=True)
        assert result is True

        result = component.evaluate_condition("ABC123", r"[a-z]+\d+", "regex", case_sensitive=True)
        assert result is False

    def test_evaluate_condition_empty_operators(self):
        """Test is empty and is not empty operators."""
        component = ConditionalRouterComponent()

        # Test is empty
        result = component.evaluate_condition("", "", "is empty", case_sensitive=True)
        assert result is True

        result = component.evaluate_condition("Hello", "", "is empty", case_sensitive=True)
        assert result is False

        # Test is not empty
        result = component.evaluate_condition("Hello", "", "is not empty", case_sensitive=True)
        assert result is True

    def test_evaluate_condition_list_operators(self):
        """Test in list and not in list operators."""
        component = ConditionalRouterComponent()

        # Test in list
        result = component.evaluate_condition("Alice", "Alice,Bob,Charlie", "in list", case_sensitive=True)
        assert result is True

        result = component.evaluate_condition("David", "Alice,Bob,Charlie", "in list", case_sensitive=True)
        assert result is False

        # Test not in list
        result = component.evaluate_condition("David", "Alice,Bob,Charlie", "not in list", case_sensitive=True)
        assert result is True

    # ==================== Test Group 5: Multi-Condition Evaluation ====================

    def test_evaluate_conditions_and_logic(self):
        """Test multi-condition evaluation with AND logic."""
        component = ConditionalRouterComponent()
        component.conditions = [
            {"field_name": "name", "operator": "equals", "compare_value": "Alice"},
            {"field_name": "age", "operator": "greater than", "compare_value": "25"},
        ]
        component.combination_logic = "AND"

        data = {"name": "Alice", "age": 30}
        result = component.evaluate_conditions(data)
        assert result is True

        data = {"name": "Alice", "age": 20}
        result = component.evaluate_conditions(data)
        assert result is False

    def test_evaluate_conditions_or_logic(self):
        """Test multi-condition evaluation with OR logic."""
        component = ConditionalRouterComponent()
        component.conditions = [
            {"field_name": "name", "operator": "equals", "compare_value": "Alice"},
            {"field_name": "name", "operator": "equals", "compare_value": "Bob"},
        ]
        component.combination_logic = "OR"

        data = {"name": "Alice"}
        result = component.evaluate_conditions(data)
        assert result is True

        data = {"name": "Charlie"}
        result = component.evaluate_conditions(data)
        assert result is False

    def test_evaluate_conditions_short_circuit(self):
        """Test short-circuit evaluation for performance."""
        component = ConditionalRouterComponent()
        component.conditions = [
            {"field_name": "name", "operator": "equals", "compare_value": "Wrong"},
            {"field_name": "age", "operator": "equals", "compare_value": "Invalid"},
        ]
        component.combination_logic = "AND"

        data = {"name": "Alice", "age": 30}
        # Should short-circuit after first condition fails
        result = component.evaluate_conditions(data)
        assert result is False

    # ==================== Test Group 6: Field Type Detection ====================

    def test_is_numeric(self):
        """Test numeric value detection."""
        component = ConditionalRouterComponent()

        assert component._is_numeric(123) is True
        assert component._is_numeric("123") is True
        assert component._is_numeric("123.45") is True
        assert component._is_numeric("abc") is False
        assert component._is_numeric("") is False

    def test_is_date_like(self):
        """Test date-like value detection."""
        component = ConditionalRouterComponent()

        assert component._is_date_like("2024-01-15") is True
        assert component._is_date_like("01/15/2024") is True
        assert component._is_date_like("01-15-2024") is True
        assert component._is_date_like("2024-01-15 10:30:00") is True
        assert component._is_date_like("not a date") is False

    # ==================== Test Group 7: Field Info Extraction ====================

    def test_extract_field_info_with_types(self):
        """Test field info extraction with type inference."""
        component = ConditionalRouterComponent()
        # Create Data object with list data properly
        records = [
            {"name": "Alice", "age": 30, "active": True, "joined": "2024-01-15"},
            {"name": "Bob", "age": 25, "active": False, "joined": "2024-02-20"},
        ]
        data = Data(data={"records": records})

        field_info_list = component.extract_field_info_with_types(data)

        # Should extract all fields
        field_names = [info.name for info in field_info_list]
        assert "name" in field_names
        assert "age" in field_names
        assert "active" in field_names
        assert "joined" in field_names

        # Check type inference
        name_field = next(info for info in field_info_list if info.name == "name")
        assert name_field.type == "string"

        age_field = next(info for info in field_info_list if info.name == "age")
        assert age_field.type == "number"

        active_field = next(info for info in field_info_list if info.name == "active")
        assert active_field.type == "boolean"

    def test_extract_nested_field_paths(self):
        """Test extraction of nested field paths."""
        component = ConditionalRouterComponent()
        data = {
            "user": {"profile": {"name": "Alice", "email": "alice@example.com"}, "settings": {"theme": "dark"}},
            "id": 123,
        }

        paths = component._extract_all_field_paths(data)

        assert "user.profile.name" in paths
        assert "user.profile.email" in paths
        assert "user.settings.theme" in paths
        assert "id" in paths

    # ==================== Test Group 8: Operator Selection ====================

    def test_get_operators_for_field_type(self):
        """Test getting appropriate operators for field types."""
        component = ConditionalRouterComponent()

        string_ops = component.get_operators_for_field_type("string")
        assert "equals" in string_ops
        assert "contains" in string_ops
        assert "regex" in string_ops
        assert "greater than" not in string_ops

        number_ops = component.get_operators_for_field_type("number")
        assert "equals" in number_ops
        assert "greater than" in number_ops
        assert "less than" in number_ops
        assert "contains" not in number_ops

        boolean_ops = component.get_operators_for_field_type("boolean")
        assert "equals" in boolean_ops
        assert "contains" not in boolean_ops
        assert "greater than" not in boolean_ops

    # ==================== Test Group 9: Caching ====================

    def test_field_info_caching(self):
        """Test that field info is cached for performance."""
        component = ConditionalRouterComponent()
        data = Data(data={"records": [{"name": "Alice", "age": 30}]})

        # First call should populate cache
        field_info_1 = component.extract_field_info_with_types(data)

        # Second call should use cache
        field_info_2 = component.extract_field_info_with_types(data)

        # Results should be identical
        assert len(field_info_1) == len(field_info_2)
        assert field_info_1[0].name == field_info_2[0].name
        assert field_info_1[0].type == field_info_2[0].type

    def test_cache_key_generation(self):
        """Test cache key generation for different data types."""
        component = ConditionalRouterComponent()

        # Test with dictionary
        key1 = component._get_cache_key({"name": "Alice"})
        assert isinstance(key1, str)

        # Test with Data object
        data = Data(data={"records": [{"name": "Alice"}]})
        key2 = component._get_cache_key(data)
        assert isinstance(key2, str)

        # Keys should be different for different data
        assert key1 != key2

    # ==================== Test Group 10: Error Handling ====================

    def test_invalid_regex_handling(self):
        """Test handling of invalid regex patterns."""
        component = ConditionalRouterComponent()

        # Invalid regex should return False and log warning
        result = component.evaluate_condition("test", "[invalid", "regex", case_sensitive=True)
        assert result is False

    def test_invalid_numeric_handling(self):
        """Test handling of invalid numeric comparisons."""
        component = ConditionalRouterComponent()

        # Non-numeric values should return False and log warning
        result = component.evaluate_condition("abc", "def", "greater than", case_sensitive=True)
        assert result is False

    def test_invalid_list_handling(self):
        """Test handling of invalid list operations."""
        component = ConditionalRouterComponent()

        # This should work fine (empty list is valid)
        result = component.evaluate_condition("Alice", "", "in list", case_sensitive=True)
        assert result is False

    # ==================== Test Group 11: Integration Tests ====================

    def test_true_response_routing(self):
        """Test true response routing with multi-conditions."""
        component = ConditionalRouterComponent()
        component.conditions = [{"field_name": "status", "operator": "equals", "compare_value": "active"}]
        component.combination_logic = "AND"
        component.true_case_message = Message(text="Routed to true")
        component.false_case_message = Message(text="Routed to false")
        component.data_input = Data(data={"records": [{"status": "active"}]})

        # Mock the iteration tracking and pre-run setup
        component._ConditionalRouterComponent__iteration_updated = True
        component._pre_run_setup()

        # Test condition evaluation directly instead of full routing
        result = component.evaluate_conditions(component.data_input)
        assert result is True

    def test_false_response_routing(self):
        """Test false response routing with multi-conditions."""
        component = ConditionalRouterComponent()
        component.conditions = [{"field_name": "status", "operator": "equals", "compare_value": "active"}]
        component.combination_logic = "AND"
        component.true_case_message = Message(text="Routed to true")
        component.false_case_message = Message(text="Routed to false")
        component.data_input = Data(data={"records": [{"status": "inactive"}]})

        # Mock the iteration tracking and pre-run setup
        component._ConditionalRouterComponent__iteration_updated = True
        component._pre_run_setup()

        # Test condition evaluation directly instead of full routing
        result = component.evaluate_conditions(component.data_input)
        assert result is False

    # ==================== Test Group 12: Legacy Mode Support ====================

    def test_legacy_mode_detection(self):
        """Test detection of legacy mode vs multi-condition mode."""
        component = ConditionalRouterComponent()

        # Mock legacy inputs
        component.input_text = "Hello World"
        component.match_text = "World"
        component.operator = "contains"

        component._pre_run_setup()
        assert component._use_legacy_mode is True

    def test_legacy_mode_condition_evaluation(self):
        """Test condition evaluation in legacy mode."""
        component = ConditionalRouterComponent()
        component.input_text = "Hello World"
        component.match_text = "World"
        component.operator = "contains"
        component.case_sensitive = True
        component.true_case_message = Message(text="Legacy true")
        component.false_case_message = Message(text="Legacy false")

        # Mock the iteration tracking and legacy mode
        component._ConditionalRouterComponent__iteration_updated = True
        component._use_legacy_mode = True

        message = component.true_response()
        assert message.text == "Legacy true"
