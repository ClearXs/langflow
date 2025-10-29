"""Unit tests for Kafka Input Component - Phase 2 (Schema Features)."""

from unittest.mock import MagicMock, patch

import pytest

from lfx.components.input_output.kafka_input import ETLKafkaInputComponent


class TestKafkaInputPhase2:
    """Test suite for Phase 2 schema features."""

    def test_message_schema_configuration(self):
        """Test that message_schema TableInput is properly configured."""
        component = ETLKafkaInputComponent()

        # Find message_schema input
        message_schema_input = None
        for inp in component.inputs:
            if inp.name == "message_schema":
                message_schema_input = inp
                break

        assert message_schema_input is not None, "message_schema input not found"
        assert message_schema_input.table_schema is not None
        assert len(message_schema_input.table_schema) == 5  # 5 columns defined

        # Verify schema columns
        column_names = [col["name"] for col in message_schema_input.table_schema]
        assert "field_name" in column_names
        assert "field_type" in column_names
        assert "json_path" in column_names
        assert "required" in column_names
        assert "description" in column_names

        # Verify action button for auto-detect
        assert message_schema_input.table_options is not None
        action_buttons = message_schema_input.table_options.get("action_buttons", [])
        assert len(action_buttons) == 1
        assert action_buttons[0]["name"] == "auto_detect_schema"

    def test_field_extraction_mode_options(self):
        """Test field_extraction_mode has correct options."""
        component = ETLKafkaInputComponent()

        # Find field_extraction_mode input
        extraction_mode_input = None
        for inp in component.inputs:
            if inp.name == "field_extraction_mode":
                extraction_mode_input = inp
                break

        assert extraction_mode_input is not None
        assert extraction_mode_input.options == ["auto", "schema_only", "flatten_all"]
        assert extraction_mode_input.value == "auto"

    def test_json_path_extraction_simple(self):
        """Test simple JSON Path extraction."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
        )

        test_data = {"user": {"name": "Alice", "age": 30}, "timestamp": "2024-01-01T00:00:00Z"}

        # Test extracting nested field
        result = component._extract_by_json_path(test_data, "$.user.name")
        assert result == "Alice"

        # Test extracting top-level field
        result = component._extract_by_json_path(test_data, "$.timestamp")
        assert result == "2024-01-01T00:00:00Z"

        # Test non-existent path
        result = component._extract_by_json_path(test_data, "$.nonexistent")
        assert result is None

    def test_json_path_extraction_edge_cases(self):
        """Test JSON Path extraction edge cases."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
        )

        test_data = {"value": 123}

        # Test without $ prefix (should return original data)
        result = component._extract_by_json_path(test_data, "value")
        assert result == test_data

        # Test empty path
        result = component._extract_by_json_path(test_data, "")
        assert result == test_data

        # Test None path
        result = component._extract_by_json_path(test_data, None)
        assert result == test_data

    def test_extract_fields_from_schema(self):
        """Test extracting fields based on schema definition."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            message_schema=[
                {"field_name": "user_name", "json_path": "$.user.name", "required": True},
                {"field_name": "user_age", "json_path": "$.user.age", "required": False},
                {"field_name": "timestamp", "json_path": "$.timestamp", "required": True},
            ],
        )

        test_message = {"user": {"name": "Bob", "age": 25}, "timestamp": "2024-01-01T12:00:00Z"}

        result = component._extract_fields_from_schema(test_message)

        assert result["user_name"] == "Bob"
        assert result["user_age"] == 25
        assert result["timestamp"] == "2024-01-01T12:00:00Z"

    def test_extract_fields_from_schema_missing_required(self):
        """Test schema extraction with missing required field."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            message_schema=[
                {"field_name": "required_field", "json_path": "$.required", "required": True},
                {"field_name": "optional_field", "json_path": "$.optional", "required": False},
            ],
        )

        # Message missing required field
        test_message = {"optional": "present"}

        result = component._extract_fields_from_schema(test_message)

        # Required field should be included even if None
        assert "required_field" in result
        assert result["required_field"] is None
        assert result["optional_field"] == "present"

    def test_process_message_schema_only_mode(self):
        """Test message processing in schema_only mode."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="schema_only",
            output_format="flattened",
            message_schema=[{"field_name": "name", "json_path": "$.user.name", "required": True}],
        )

        test_message = {
            "user": {
                "name": "Charlie",
                "email": "charlie@example.com",  # Not in schema
            }
        }

        result = component._process_message(test_message)

        # Only schema-defined fields should be extracted
        assert "name" in result
        assert result["name"] == "Charlie"
        # Email should not be included (not in schema)
        assert "email" not in result
        assert "user_email" not in result

    def test_process_message_flatten_all_mode(self):
        """Test message processing in flatten_all mode."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="flatten_all",
            output_format="flattened",
        )

        test_message = {"user": {"name": "David", "profile": {"age": 35, "city": "NYC"}}}

        result = component._process_message(test_message)

        # All fields should be flattened
        assert "user_name" in result
        assert result["user_name"] == "David"
        assert "user_profile_age" in result
        assert result["user_profile_age"] == 35
        assert "user_profile_city" in result
        assert result["user_profile_city"] == "NYC"

    def test_process_message_auto_mode_with_schema(self):
        """Test message processing in auto mode with schema defined."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="auto",
            output_format="flattened",
            message_schema=[{"field_name": "username", "json_path": "$.user.name", "required": True}],
        )

        test_message = {"user": {"name": "Eve", "email": "eve@example.com"}}

        result = component._process_message(test_message)

        # Auto mode should use schema when defined
        assert "username" in result
        assert result["username"] == "Eve"

    def test_process_message_auto_mode_without_schema(self):
        """Test message processing in auto mode without schema (fallback to flatten)."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="auto",
            output_format="flattened",
        )

        test_message = {"level1": {"level2": "value"}}

        result = component._process_message(test_message)

        # Should fallback to flatten_all
        assert "level1_level2" in result
        assert result["level1_level2"] == "value"

    def test_process_message_raw_output_format(self):
        """Test message processing with raw output format."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="auto",
            output_format="raw",
            message_schema=[{"field_name": "name", "json_path": "$.user.name", "required": True}],
        )

        test_message = {"user": {"name": "Frank"}}

        result = component._process_message(test_message)

        # Raw format should preserve structure from schema extraction
        assert result["name"] == "Frank"

    def test_analyze_sample_data_for_schema(self):
        """Test schema analysis from sample data."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
        )

        samples = [
            {"user_id": 1, "username": "alice", "score": 95.5, "active": True, "metadata": {"key": "value"}},
            {"user_id": 2, "username": "bob", "score": 87.0, "active": False, "metadata": {"key": "value"}},
            {"user_id": 3, "username": "charlie", "score": 92.3, "active": True},
        ]

        schema = component._analyze_sample_data_for_schema(samples)

        # Verify schema structure
        assert len(schema) >= 4  # At least user_id, username, score, active

        # Find specific fields
        user_id_field = next(f for f in schema if f["field_name"] == "user_id")
        username_field = next(f for f in schema if f["field_name"] == "username")
        score_field = next(f for f in schema if f["field_name"] == "score")
        active_field = next(f for f in schema if f["field_name"] == "active")
        metadata_field = next((f for f in schema if f["field_name"] == "metadata"), None)

        # Verify field types
        assert user_id_field["field_type"] == "int"
        assert username_field["field_type"] == "string"
        assert score_field["field_type"] == "float"
        assert active_field["field_type"] == "bool"
        if metadata_field:
            assert metadata_field["field_type"] == "json"

        # Verify required flags
        assert user_id_field["required"] is True  # Present in all samples
        assert username_field["required"] is True
        assert score_field["required"] is True
        if metadata_field:
            assert metadata_field["required"] is False  # Missing in third sample

        # Verify JSON paths
        assert user_id_field["json_path"] == "$.user_id"
        assert username_field["json_path"] == "$.username"

    def test_analyze_sample_data_empty_samples(self):
        """Test schema analysis with empty samples."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
        )

        schema = component._analyze_sample_data_for_schema([])

        assert schema == []

    def test_analyze_sample_data_non_dict_samples(self):
        """Test schema analysis with non-dictionary samples."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
        )

        samples = ["string1", "string2", 123]

        schema = component._analyze_sample_data_for_schema(samples)

        # Should handle gracefully and return empty or minimal schema
        assert isinstance(schema, list)

    @patch("confluent_kafka.Consumer")
    def test_update_build_config_auto_detect_schema(self, mock_consumer_class):
        """Test update_build_config with auto_detect_schema action."""
        # Mock consumer and messages
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        # Create mock messages
        mock_message1 = MagicMock()
        mock_message1.value.return_value = b'{"user_id": 1, "username": "alice"}'
        mock_message1.error.return_value = None

        mock_message2 = MagicMock()
        mock_message2.value.return_value = b'{"user_id": 2, "username": "bob"}'
        mock_message2.error.return_value = None

        mock_consumer.poll.side_effect = [mock_message1, mock_message2, None, None, None]

        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092", topics="test-topic", value_deserializer="json"
        )

        build_config = {"message_schema": {"value": []}}

        result = component.update_build_config(
            build_config, field_value="auto_detect_schema", field_name="message_schema"
        )

        # Verify schema was populated
        assert "message_schema" in result
        schema_value = result["message_schema"]["value"]
        assert len(schema_value) > 0

        # Verify consumer was called
        mock_consumer_class.assert_called_once()
        mock_consumer.subscribe.assert_called_once()
        mock_consumer.close.assert_called_once()

    def test_get_consumer_info_includes_schema_info(self):
        """Test that get_consumer_info includes schema-related information."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="schema_only",
            message_schema=[
                {"field_name": "field1", "json_path": "$.field1"},
                {"field_name": "field2", "json_path": "$.field2"},
            ],
        )

        info = component.get_consumer_info()

        assert info.data["field_extraction_mode"] == "schema_only"
        assert info.data["schema_defined"] is True
        assert info.data["schema_fields"] == 2

    def test_sample_data_cache_integration(self):
        """Test that sample data cache works with schema processing."""
        component = ETLKafkaInputComponent(
            bootstrap_servers="localhost:9092",
            topics="test-topic",
            field_extraction_mode="schema_only",
            output_format="flattened",
            message_schema=[{"field_name": "id", "json_path": "$.id", "required": True}],
        )

        # Simulate adding to cache (would happen during streaming)
        component._sample_data_cache = [{"id": 1}, {"id": 2}, {"id": 3}]

        sample_data = component.get_sample_data()

        assert len(sample_data) == 3
        assert sample_data[0].data["id"] == 1
        assert sample_data[1].data["id"] == 2
        assert sample_data[2].data["id"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
