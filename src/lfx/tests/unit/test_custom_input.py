"""Unit tests for Custom Input Component."""

from datetime import datetime

import pytest

from lfx.components.input_output.custom_input import ETLCustomInputComponent
from lfx.schema import Data


class TestCustomInputComponent:
    """Test suite for ETLCustomInputComponent."""

    @pytest.fixture
    def basic_field_schema(self):
        """Basic field schema for testing."""
        return [
            {"field_name": "id", "data_type": "integer", "default_value": "1"},
            {"field_name": "name", "data_type": "string", "default_value": "Test User"},
            {"field_name": "email", "data_type": "string", "default_value": "test@example.com"},
            {"field_name": "age", "data_type": "integer", "default_value": "25"},
            {"field_name": "score", "data_type": "float", "default_value": "95.5"},
            {"field_name": "is_active", "data_type": "boolean", "default_value": "true"},
            {"field_name": "created_at", "data_type": "datetime", "default_value": "2025-01-01T00:00:00"},
        ]

    @pytest.fixture
    def sample_data_rows(self):
        """Sample data rows matching the basic schema."""
        return [
            {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "score": 88.5,
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
            },
            {
                "id": 2,
                "name": "Jane Smith",
                "email": "jane@example.com",
                "age": 28,
                "score": 92.0,
                "is_active": False,
                "created_at": "2025-02-20T14:45:00",
            },
        ]

    def test_component_initialization(self):
        """Test that component initializes correctly."""
        component = ETLCustomInputComponent()
        assert component.display_name is not None
        assert component.description is not None
        assert component.name == "ETLCustomInput"
        assert component.icon == "TestTube2"

    def test_generate_schema_from_fields(self, basic_field_schema):
        """Test schema generation from field definitions."""
        component = ETLCustomInputComponent()
        table_schema = component._generate_schema_from_fields(basic_field_schema)

        assert len(table_schema) == 7
        assert table_schema[0]["name"] == "id"
        assert table_schema[0]["type"] == "int"
        assert table_schema[1]["name"] == "name"
        assert table_schema[1]["type"] == "str"
        assert table_schema[4]["name"] == "score"
        assert table_schema[4]["type"] == "float"
        assert table_schema[5]["name"] == "is_active"
        assert table_schema[5]["type"] == "bool"

    def test_generate_schema_empty_field_name(self):
        """Test schema generation skips fields with empty names."""
        component = ETLCustomInputComponent()
        field_schema = [
            {"field_name": "", "data_type": "string", "default_value": ""},
            {"field_name": "valid_field", "data_type": "integer", "default_value": "0"},
        ]

        table_schema = component._generate_schema_from_fields(field_schema)
        assert len(table_schema) == 1
        assert table_schema[0]["name"] == "valid_field"

    def test_convert_value_string(self):
        """Test string type conversion."""
        component = ETLCustomInputComponent()

        assert component._convert_value("hello", "string") == "hello"
        assert component._convert_value(123, "string") == "123"
        assert component._convert_value(True, "string") == "True"

    def test_convert_value_integer(self):
        """Test integer type conversion."""
        component = ETLCustomInputComponent()

        assert component._convert_value("42", "integer") == 42
        assert component._convert_value(42, "integer") == 42
        assert component._convert_value("100", "integer") == 100

        with pytest.raises(ValueError):
            component._convert_value("not a number", "integer")

    def test_convert_value_float(self):
        """Test float type conversion."""
        component = ETLCustomInputComponent()

        assert component._convert_value("3.14", "float") == 3.14
        assert component._convert_value(3.14, "float") == 3.14
        assert component._convert_value("100", "float") == 100.0

        with pytest.raises(ValueError):
            component._convert_value("not a float", "float")

    def test_convert_value_boolean(self):
        """Test boolean type conversion."""
        component = ETLCustomInputComponent()

        # Test various true values
        assert component._convert_value("true", "boolean") is True
        assert component._convert_value("True", "boolean") is True
        assert component._convert_value("TRUE", "boolean") is True
        assert component._convert_value("1", "boolean") is True
        assert component._convert_value("yes", "boolean") is True
        assert component._convert_value("y", "boolean") is True
        assert component._convert_value("on", "boolean") is True
        assert component._convert_value(True, "boolean") is True

        # Test various false values
        assert component._convert_value("false", "boolean") is False
        assert component._convert_value("False", "boolean") is False
        assert component._convert_value("FALSE", "boolean") is False
        assert component._convert_value("0", "boolean") is False
        assert component._convert_value("no", "boolean") is False
        assert component._convert_value("n", "boolean") is False
        assert component._convert_value("off", "boolean") is False
        assert component._convert_value(False, "boolean") is False

        with pytest.raises(ValueError):
            component._convert_value("maybe", "boolean")

    def test_convert_value_datetime(self):
        """Test datetime type conversion."""
        component = ETLCustomInputComponent()

        # ISO format
        result = component._convert_value("2025-01-15T10:30:00", "datetime")
        assert isinstance(result, str)
        assert "2025-01-15" in result

        # Various datetime formats
        result = component._convert_value("2025-01-15", "datetime")
        assert "2025-01-15" in result

        # Already datetime object
        dt = datetime(2025, 1, 15, 10, 30)
        result = component._convert_value(dt, "datetime")
        assert isinstance(result, str)

        with pytest.raises(ValueError):
            component._convert_value("not a date", "datetime")

    def test_convert_value_null_or_empty(self):
        """Test conversion of null/empty values."""
        component = ETLCustomInputComponent()

        assert component._convert_value(None, "string") is None
        assert component._convert_value("", "string") is None
        assert component._convert_value(None, "integer") is None
        assert component._convert_value("", "integer") is None

    def test_generate_test_data(self, basic_field_schema):
        """Test test data generation."""
        component = ETLCustomInputComponent()
        test_data = component._generate_test_data(basic_field_schema, 10)

        assert len(test_data) == 10

        # Verify first row uses default values
        first_row = test_data[0]
        assert first_row["id"] == 1
        assert first_row["name"] == "Test User"
        assert first_row["email"] == "test@example.com"

        # Verify all rows have all fields
        for row in test_data:
            assert "id" in row
            assert "name" in row
            assert "email" in row
            assert "age" in row
            assert "score" in row
            assert "is_active" in row
            assert "created_at" in row

        # Verify data types
        for row in test_data:
            assert isinstance(row["id"], int)
            assert isinstance(row["name"], str)
            assert isinstance(row["email"], str)
            assert isinstance(row["age"], int)
            assert isinstance(row["score"], (int, float))
            assert isinstance(row["is_active"], bool)
            assert isinstance(row["created_at"], str)

    def test_generate_sample_value_string_contextual(self):
        """Test contextual string generation for different field names."""
        component = ETLCustomInputComponent()

        # Email field
        email = component._generate_sample_value("email", "string", 0)
        assert "@" in email

        # Name fields
        first_name = component._generate_sample_value("first_name", "string", 0)
        assert len(first_name) > 0

        # Phone field
        phone = component._generate_sample_value("phone_number", "string", 0)
        assert "555" in phone or len(phone) > 0

    def test_generate_sample_value_integer_contextual(self):
        """Test contextual integer generation."""
        component = ETLCustomInputComponent()

        # ID field - should be sequential
        id_value = component._generate_sample_value("id", "integer", 5)
        assert id_value == 6  # index + 1

        # Age field - should be reasonable
        age = component._generate_sample_value("age", "integer", 0)
        assert 18 <= age <= 80

    def test_generate_sample_value_float_contextual(self):
        """Test contextual float generation."""
        component = ETLCustomInputComponent()

        price = component._generate_sample_value("price", "float", 0)
        assert isinstance(price, float)
        assert price >= 0

        score = component._generate_sample_value("score", "float", 0)
        assert isinstance(score, float)

    def test_generate_sample_value_boolean(self):
        """Test boolean sample value generation."""
        component = ETLCustomInputComponent()

        value = component._generate_sample_value("is_active", "boolean", 0)
        assert isinstance(value, bool)

    def test_generate_sample_value_datetime(self):
        """Test datetime sample value generation."""
        component = ETLCustomInputComponent()

        value = component._generate_sample_value("created_at", "datetime", 0)
        assert isinstance(value, str)
        # Should be ISO format
        assert "T" in value or "-" in value

    def test_validate_data_row_success(self, basic_field_schema, sample_data_rows):
        """Test successful data row validation."""
        component = ETLCustomInputComponent()

        validated_row = component._validate_data_row(
            sample_data_rows[0], basic_field_schema, strict_validation=True, row_index=0
        )

        assert validated_row["id"] == 1
        assert validated_row["name"] == "John Doe"
        assert validated_row["age"] == 30
        assert validated_row["is_active"] is True

    def test_validate_data_row_type_conversion(self, basic_field_schema):
        """Test data row validation with type conversion."""
        component = ETLCustomInputComponent()

        # String representations of values
        row = {
            "id": "10",
            "name": "Test",
            "email": "test@test.com",
            "age": "35",
            "score": "88.5",
            "is_active": "true",
            "created_at": "2025-01-01",
        }

        validated_row = component._validate_data_row(row, basic_field_schema, strict_validation=True, row_index=0)

        assert validated_row["id"] == 10
        assert validated_row["age"] == 35
        assert validated_row["score"] == 88.5
        assert validated_row["is_active"] is True

    def test_validate_data_row_strict_mode_failure(self, basic_field_schema):
        """Test data row validation fails in strict mode with invalid data."""
        component = ETLCustomInputComponent()

        invalid_row = {
            "id": "not a number",
            "name": "Test",
            "email": "test@test.com",
            "age": "25",
            "score": "88.5",
            "is_active": "true",
            "created_at": "2025-01-01",
        }

        with pytest.raises(ValueError) as exc_info:
            component._validate_data_row(invalid_row, basic_field_schema, strict_validation=True, row_index=0)

        assert "Row 1" in str(exc_info.value)
        assert "id" in str(exc_info.value)

    def test_validate_data_row_non_strict_mode(self, basic_field_schema):
        """Test data row validation in non-strict mode keeps original values."""
        component = ETLCustomInputComponent()

        invalid_row = {
            "id": "not a number",
            "name": "Test",
            "email": "test@test.com",
            "age": "25",
            "score": "88.5",
            "is_active": "true",
            "created_at": "2025-01-01",
        }

        # Should not raise in non-strict mode
        validated_row = component._validate_data_row(
            invalid_row, basic_field_schema, strict_validation=False, row_index=0
        )

        # Invalid field keeps original value
        assert validated_row["id"] == "not a number"
        # Valid fields are converted
        assert validated_row["age"] == 25

    def test_load_data_success(self, basic_field_schema, sample_data_rows):
        """Test successful data loading."""
        component = ETLCustomInputComponent(
            field_schema=basic_field_schema, data_table=sample_data_rows, strict_validation=True
        )

        result = component.load_data()

        assert len(result) == 2
        assert all(isinstance(item, Data) for item in result)

        # Verify first row data
        first_data = result[0].data
        assert first_data["id"] == 1
        assert first_data["name"] == "John Doe"
        assert first_data["email"] == "john@example.com"

    def test_load_data_empty_schema(self):
        """Test load_data with empty schema returns empty sample."""
        component = ETLCustomInputComponent(field_schema=[], data_table=[])

        result = component.load_data()

        assert len(result) == 1
        assert isinstance(result[0], Data)
        assert result[0].data == {}

    def test_load_data_empty_data_table(self, basic_field_schema):
        """Test load_data with empty data table returns sample record."""
        component = ETLCustomInputComponent(field_schema=basic_field_schema, data_table=[])

        result = component.load_data()

        assert len(result) == 1
        assert isinstance(result[0], Data)

        # Should have all fields from schema with None values
        assert "id" in result[0].data
        assert "name" in result[0].data
        assert "email" in result[0].data

    def test_update_build_config_apply_schema(self, basic_field_schema):
        """Test update_build_config auto-syncs schema when field_schema changes."""
        component = ETLCustomInputComponent()

        build_config = {
            "field_schema": {"value": basic_field_schema},
            "data_table": {"value": [], "table_schema": []},
            "test_rows_count": {"value": 10},
            "strict_validation": {"value": True},
        }

        # Schema auto-syncs when field_schema changes (no action needed)
        updated_config = component.update_build_config(
            build_config,
            field_value=basic_field_schema,
            field_name="field_schema",
            action=None,  # No action button, auto-sync on change
        )

        # Check that data_table schema was updated
        assert len(updated_config["data_table"]["table_schema"]) == 7
        assert updated_config["data_table"]["table_schema"][0]["name"] == "id"
        # Check that data was cleared
        assert updated_config["data_table"]["value"] == []

    def test_update_build_config_duplicate_field_names(self):
        """Test update_build_config detects duplicate field names during auto-sync."""
        component = ETLCustomInputComponent()

        duplicate_schema = [
            {"field_name": "id", "data_type": "integer", "default_value": "1"},
            {"field_name": "name", "data_type": "string", "default_value": "Test"},
            {"field_name": "id", "data_type": "string", "default_value": "dup"},
        ]

        build_config = {
            "field_schema": {"value": duplicate_schema},
            "data_table": {"value": [], "table_schema": []},
        }

        # Auto-sync when field_schema changes
        updated_config = component.update_build_config(
            build_config, field_value=duplicate_schema, field_name="field_schema", action=None
        )

        # Schema should not be applied due to duplicate
        assert component.status is not None
        # Check for i18n key or translated text
        assert "duplicate_field" in component.status or "id" in component.status or "重复" in component.status

    def test_update_build_config_generate_test_data(self, basic_field_schema):
        """Test update_build_config generate test data action."""
        component = ETLCustomInputComponent()

        build_config = {
            "field_schema": {"value": basic_field_schema},
            "data_table": {"value": [], "table_schema": []},
            "test_rows_count": {"value": 5},
            "strict_validation": {"value": True},
        }

        updated_config = component.update_build_config(
            build_config, field_value=None, field_name="data_table", action="generate_test_data"
        )

        # Check that test data was generated
        assert len(updated_config["data_table"]["value"]) == 5
        # Verify first row has default values
        assert updated_config["data_table"]["value"][0]["id"] == 1

    def test_update_build_config_validate_data(self, basic_field_schema, sample_data_rows):
        """Test update_build_config validate data action."""
        component = ETLCustomInputComponent()

        # First generate the correct schema from field_schema
        expected_schema = component._generate_schema_from_fields(basic_field_schema)

        build_config = {
            "field_schema": {"value": basic_field_schema},
            "data_table": {"value": sample_data_rows, "table_schema": expected_schema},
            "strict_validation": {"value": True},
        }

        updated_config = component.update_build_config(
            build_config, field_value=None, field_name="data_table", action="validate_data"
        )

        # Validation should succeed - check for i18n key or translated text
        assert "validation_passed" in component.status or "2" in component.status or "验证通过" in component.status

    def test_update_build_config_validate_invalid_data(self, basic_field_schema):
        """Test update_build_config validate data action with invalid data."""
        component = ETLCustomInputComponent()

        invalid_data = [
            {
                "id": "not a number",
                "name": "Test",
                "email": "test@test.com",
                "age": "25",
                "score": "88.5",
                "is_active": "true",
                "created_at": "2025-01-01",
            }
        ]

        # First generate the correct schema from field_schema
        expected_schema = component._generate_schema_from_fields(basic_field_schema)

        build_config = {
            "field_schema": {"value": basic_field_schema},
            "data_table": {"value": invalid_data, "table_schema": expected_schema},
            "strict_validation": {"value": True},
        }

        updated_config = component.update_build_config(
            build_config, field_value=None, field_name="data_table", action="validate_data"
        )

        # Validation should fail
        assert "失败" in component.status or "failed" in component.status.lower()

    def test_component_with_all_data_types(self):
        """Integration test with all supported data types."""
        field_schema = [
            {"field_name": "str_field", "data_type": "string", "default_value": "test"},
            {"field_name": "int_field", "data_type": "integer", "default_value": "42"},
            {"field_name": "float_field", "data_type": "float", "default_value": "3.14"},
            {"field_name": "bool_field", "data_type": "boolean", "default_value": "true"},
            {"field_name": "datetime_field", "data_type": "datetime", "default_value": "2025-01-01"},
        ]

        data_rows = [
            {
                "str_field": "value1",
                "int_field": "100",
                "float_field": "99.99",
                "bool_field": "false",
                "datetime_field": "2025-06-15T12:00:00",
            }
        ]

        component = ETLCustomInputComponent(field_schema=field_schema, data_table=data_rows, strict_validation=True)

        result = component.load_data()

        assert len(result) == 1
        data = result[0].data

        assert data["str_field"] == "value1"
        assert data["int_field"] == 100
        assert data["float_field"] == 99.99
        assert data["bool_field"] is False
        assert isinstance(data["datetime_field"], str)
