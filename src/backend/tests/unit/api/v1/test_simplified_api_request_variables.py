"""Test variable handling in SimplifiedAPIRequest."""

import json

from langflow.api.v1.schemas import SimplifiedAPIRequest


class TestSimplifiedAPIRequestVariables:
    """Test variable handling in SimplifiedAPIRequest."""

    def test_runtime_variables_explicit(self):
        """Test that explicit runtime_variables field works."""
        request = SimplifiedAPIRequest(runtime_variables={"key1": "value1", "key2": "value2"})
        assert request.runtime_variables == {"key1": "value1", "key2": "value2"}
        assert request.variables is None  # Should be cleared

    def test_variables_field_alias(self):
        """Test 'variables' as alias for runtime_variables."""
        request = SimplifiedAPIRequest(variables={"key1": "value1", "key2": "value2"})
        # Should be merged into runtime_variables
        assert request.runtime_variables == {"key1": "value1", "key2": "value2"}
        assert request.variables is None  # Should be cleared

    def test_auto_wrap_extra_fields(self):
        """Test auto-wrapping of unrecognized top-level fields."""
        data = {
            "input_value": "test",
            "folderId": "123",
            "resultId": "456",
            "taskId": "789",
            "dataType": "SPATIAL_DATA_BODY",
        }
        request = SimplifiedAPIRequest(**data)

        # Standard field should be set normally
        assert request.input_value == "test"

        # Extra fields should be auto-wrapped into runtime_variables
        assert request.runtime_variables is not None
        assert request.runtime_variables["folderId"] == "123"
        assert request.runtime_variables["resultId"] == "456"
        assert request.runtime_variables["taskId"] == "789"
        assert request.runtime_variables["dataType"] == "SPATIAL_DATA_BODY"

    def test_priority_runtime_over_variables(self):
        """Test that runtime_variables takes precedence over variables."""
        request = SimplifiedAPIRequest(
            runtime_variables={"key1": "from_runtime", "key2": "runtime_only"},
            variables={"key1": "from_variables", "key3": "variables_only"},
        )
        # runtime_variables wins for key1
        assert request.runtime_variables["key1"] == "from_runtime"
        # key2 from runtime_variables is preserved
        assert request.runtime_variables["key2"] == "runtime_only"
        # variables field should be cleared
        assert request.variables is None

    def test_priority_runtime_over_extra_fields(self):
        """Test that runtime_variables takes precedence over auto-wrapped fields."""
        data = {
            "runtime_variables": {"folderId": "from_runtime", "key1": "runtime"},
            "folderId": "from_extra",  # Should be ignored (runtime_variables wins)
            "resultId": "456",  # Should be added (no conflict)
        }
        request = SimplifiedAPIRequest(**data)

        # runtime_variables wins for folderId
        assert request.runtime_variables["folderId"] == "from_runtime"
        # key1 from runtime_variables is preserved
        assert request.runtime_variables["key1"] == "runtime"
        # resultId from extra fields is added (no conflict)
        assert request.runtime_variables["resultId"] == "456"

    def test_priority_variables_over_extra_fields(self):
        """Test that variables field takes precedence over auto-wrapped fields."""
        data = {
            "variables": {"folderId": "from_variables", "key1": "var"},
            "folderId": "from_extra",  # Should be ignored
            "resultId": "456",  # Should be added
        }
        request = SimplifiedAPIRequest(**data)

        # variables wins for folderId (becomes runtime_variables)
        assert request.runtime_variables["folderId"] == "from_variables"
        # key1 from variables is preserved
        assert request.runtime_variables["key1"] == "var"
        # resultId from extra fields is added
        assert request.runtime_variables["resultId"] == "456"

    def test_all_three_sources_combined(self):
        """Test all three variable sources: runtime_variables, variables, extra fields."""
        data = {
            "input_value": "test",
            "runtime_variables": {"key1": "runtime", "key_rt": "only_runtime"},
            "variables": {"key2": "variables", "key_var": "only_variables"},
            "key3": "extra",
            "key_extra": "only_extra",
        }
        request = SimplifiedAPIRequest(**data)

        # Standard field is set normally
        assert request.input_value == "test"

        # runtime_variables has highest priority
        assert request.runtime_variables["key1"] == "runtime"
        assert request.runtime_variables["key_rt"] == "only_runtime"

        # variables fields that don't conflict are included
        assert request.runtime_variables["key_var"] == "only_variables"

        # extra fields that don't conflict are included
        assert request.runtime_variables["key_extra"] == "only_extra"
        assert request.runtime_variables["key3"] == "extra"

        # Standard field should NOT be in runtime_variables
        assert "input_value" not in request.runtime_variables

    def test_type_conversion_integers(self):
        """Test that integer values are converted to strings."""
        data = {"folderId": 123, "resultId": 456, "count": 0}
        request = SimplifiedAPIRequest(**data)

        assert request.runtime_variables["folderId"] == "123"
        assert request.runtime_variables["resultId"] == "456"
        assert request.runtime_variables["count"] == "0"
        assert all(isinstance(v, str) for v in request.runtime_variables.values())

    def test_type_conversion_floats(self):
        """Test that float values are converted to strings."""
        data = {"price": 19.99, "score": 0.95}
        request = SimplifiedAPIRequest(**data)

        assert request.runtime_variables["price"] == "19.99"
        assert request.runtime_variables["score"] == "0.95"

    def test_type_conversion_booleans(self):
        """Test that boolean values are converted to 'true'/'false' strings."""
        data = {
            "isActive": True,
            "isDeleted": False,
        }
        request = SimplifiedAPIRequest(**data)

        assert request.runtime_variables["isActive"] == "true"
        assert request.runtime_variables["isDeleted"] == "false"

    def test_type_conversion_none(self):
        """Test that None values are converted to empty strings."""
        data = {"variables": {"optionalField": None, "emptyField": None}}
        request = SimplifiedAPIRequest(**data)

        assert request.runtime_variables["optionalField"] == ""
        assert request.runtime_variables["emptyField"] == ""

    def test_type_conversion_nested_objects(self):
        """Test that nested objects are converted to JSON strings."""
        data = {"metadata": {"key": "value", "count": 42, "active": True}, "tags": ["tag1", "tag2", "tag3"]}
        request = SimplifiedAPIRequest(**data)

        # Should be JSON strings
        metadata = json.loads(request.runtime_variables["metadata"])
        assert metadata["key"] == "value"
        assert metadata["count"] == 42
        assert metadata["active"] is True

        tags = json.loads(request.runtime_variables["tags"])
        assert tags == ["tag1", "tag2", "tag3"]

    def test_empty_request(self):
        """Test that empty request doesn't create runtime_variables."""
        request = SimplifiedAPIRequest()

        # Should not create empty runtime_variables dict
        assert request.runtime_variables is None

    def test_only_standard_fields(self):
        """Test request with only standard fields (no variables)."""
        data = {"input_value": "test input", "input_type": "chat", "session_id": "session-123"}
        request = SimplifiedAPIRequest(**data)

        # Standard fields are set
        assert request.input_value == "test input"
        assert request.input_type == "chat"
        assert request.session_id == "session-123"

        # No runtime_variables should be created
        assert request.runtime_variables is None

    def test_mixed_standard_and_custom_fields(self):
        """Test request with both standard and custom fields."""
        data = {
            "input_value": "test input",
            "session_id": "session-123",
            "customField": "custom value",
            "folderId": 999,
        }
        request = SimplifiedAPIRequest(**data)

        # Standard fields are set normally
        assert request.input_value == "test input"
        assert request.session_id == "session-123"

        # Custom fields are auto-wrapped
        assert request.runtime_variables["customField"] == "custom value"
        assert request.runtime_variables["folderId"] == "999"

        # Standard fields should NOT be in runtime_variables
        assert "input_value" not in request.runtime_variables
        assert "session_id" not in request.runtime_variables

    def test_empty_dicts(self):
        """Test that empty variable dicts are handled correctly."""
        data = {
            "runtime_variables": {},
            "variables": {},
        }
        request = SimplifiedAPIRequest(**data)

        # Empty dict should not create runtime_variables
        # (the validator should detect it's empty and not set it)
        assert request.runtime_variables == {} or request.runtime_variables is None

    def test_backwards_compatibility_runtime_variables_only(self):
        """Test that existing usage with runtime_variables continues to work."""
        request = SimplifiedAPIRequest(
            input_value="test",
            runtime_variables={"API_KEY": "secret", "USER_ID": "12345", "REGION": "us-east-1"},
        )

        assert request.input_value == "test"
        assert request.runtime_variables["API_KEY"] == "secret"
        assert request.runtime_variables["USER_ID"] == "12345"
        assert request.runtime_variables["REGION"] == "us-east-1"

    def test_user_example_folderId(self):
        """Test the actual user's example case that was failing."""
        data = {
            "resultId": 2002944268457213953,
            "dataType": "SPATIAL_DATA_BODY",
            "taskId": 2002944268289441794,
            "folderId": 1937069843168202754,
        }
        request = SimplifiedAPIRequest(**data)

        # All fields should be auto-wrapped and converted to strings
        assert request.runtime_variables["resultId"] == "2002944268457213953"
        assert request.runtime_variables["dataType"] == "SPATIAL_DATA_BODY"
        assert request.runtime_variables["taskId"] == "2002944268289441794"
        assert request.runtime_variables["folderId"] == "1937069843168202754"
