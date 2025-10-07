import json
import pytest
from unittest.mock import Mock, patch

from lfx.components.data.data_validator import DataValidatorComponent
from lfx.schema.data import Data


class TestDataValidatorComponent:
    """Test suite for DataValidatorComponent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.component = DataValidatorComponent()

        # Mock translation function to return key
        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            self.component.display_name = "Data Validator"
            self.component.description = "Test data validator"

    def test_component_initialization(self):
        """Test component initializes correctly."""
        assert self.component.display_name == "Data Validator"
        assert self.component.icon == "check-circle"
        assert self.component.name == "DataValidator"
        assert len(self.component.inputs) == 13
        assert len(self.component.outputs) == 3

    def test_parse_input_data_list_of_data_objects(self):
        """Test parsing list of Data objects."""
        data_objects = [
            Data(data={"id": 1, "name": "John"}),
            Data(data={"id": 2, "name": "Jane"})
        ]
        self.component.data = data_objects

        result = self.component._parse_input_data()

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "John"}
        assert result[1] == {"id": 2, "name": "Jane"}

    def test_parse_input_data_single_data_object(self):
        """Test parsing single Data object."""
        data_object = Data(data={"id": 1, "name": "John"})
        self.component.data = data_object

        result = self.component._parse_input_data()

        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "John"}

    def test_parse_input_data_json_string(self):
        """Test parsing JSON string."""
        json_data = json.dumps([{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}])
        self.component.data = json_data

        result = self.component._parse_input_data()

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "John"}
        assert result[1] == {"id": 2, "name": "Jane"}

    def test_parse_input_data_invalid_json(self):
        """Test parsing invalid JSON string raises error."""
        self.component.data = "invalid json"

        with pytest.raises(ValueError):
            self.component._parse_input_data()

    def test_check_null_values(self):
        """Test null value validation."""
        record = {"id": 1, "name": "John", "email": "", "phone": None}

        errors = self.component._check_null_values(record, 0)

        assert len(errors) == 2
        assert any(error["field"] == "email" for error in errors)
        assert any(error["field"] == "phone" for error in errors)
        assert all(error["type"] == "null_value" for error in errors)

    def test_validate_type_string(self):
        """Test string type validation."""
        assert self.component._validate_type("hello", "string") is True
        assert self.component._validate_type(123, "string") is False

    def test_validate_type_integer(self):
        """Test integer type validation."""
        assert self.component._validate_type(123, "integer") is True
        assert self.component._validate_type("123", "integer") is True
        assert self.component._validate_type("hello", "integer") is False
        assert self.component._validate_type(12.3, "integer") is False

    def test_validate_type_float(self):
        """Test float type validation."""
        assert self.component._validate_type(12.3, "float") is True
        assert self.component._validate_type("12.3", "float") is True
        assert self.component._validate_type("hello", "float") is False

    def test_validate_type_email(self):
        """Test email type validation."""
        assert self.component._validate_type("test@example.com", "email") is True
        assert self.component._validate_type("invalid-email", "email") is False
        assert self.component._validate_type(123, "email") is False

    def test_validate_type_boolean(self):
        """Test boolean type validation."""
        assert self.component._validate_type(True, "boolean") is True
        assert self.component._validate_type(False, "boolean") is True
        assert self.component._validate_type("true", "boolean") is False

    def test_check_data_types(self):
        """Test data type validation against schema."""
        self.component.type_schema = '{"id": "integer", "name": "string", "email": "email"}'
        record = {"id": "not_int", "name": "John", "email": "invalid-email"}

        errors = self.component._check_data_types(record, 0)

        assert len(errors) == 2
        error_fields = [error["field"] for error in errors]
        assert "id" in error_fields
        assert "email" in error_fields

    def test_check_ranges(self):
        """Test range validation."""
        self.component.range_schema = '{"age": {"min": 0, "max": 120}, "score": {"min": 0}}'
        record = {"age": -5, "score": -10, "other": 50}

        errors = self.component._check_ranges(record, 0)

        assert len(errors) == 2
        error_fields = [error["field"] for error in errors]
        assert "age" in error_fields
        assert "score" in error_fields

    def test_check_custom_rules_pattern(self):
        """Test custom rule pattern validation."""
        self.component.custom_rules = '{"company_email": {"field": "email", "pattern": ".*@company\\\\.com$"}}'
        record = {"email": "user@gmail.com"}

        errors = self.component._check_custom_rules(record, 0)

        assert len(errors) == 1
        assert errors[0]["rule_name"] == "company_email"

    def test_check_custom_rules_length(self):
        """Test custom rule length validation."""
        self.component.custom_rules = '{"name_length": {"field": "name", "min_length": 3, "max_length": 10}}'
        record = {"name": "Jo"}

        errors = self.component._check_custom_rules(record, 0)

        assert len(errors) == 1
        assert "min_length" in errors[0]["constraint"]

    def test_check_duplicates(self):
        """Test duplicate detection."""
        data_list = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"},
            {"id": 1, "name": "John"}  # Duplicate
        ]

        errors = self.component._check_duplicates(data_list)

        assert len(errors) == 1
        assert errors[0]["type"] == "duplicate"
        assert errors[0]["record_index"] == 2
        assert errors[0]["duplicate_of"] == 0

    def test_generate_statistics(self):
        """Test statistics generation."""
        data_list = [
            {"id": 1, "name": "John", "age": 30},
            {"id": 2, "name": "", "age": 25},
            {"id": 3, "name": "Bob", "age": None}
        ]

        stats = self.component._generate_statistics(data_list)

        assert stats["record_count"] == 3
        assert "field_analysis" in stats
        assert "data_quality_score" in stats
        assert "name" in stats["field_analysis"]
        assert stats["field_analysis"]["name"]["null_count"] == 1  # Empty string counts as null
        assert stats["field_analysis"]["age"]["null_count"] == 1  # None value

    def test_validate_data_success(self):
        """Test successful validation with valid data."""
        self.component.data = [
            Data(data={"id": 1, "name": "John", "email": "john@example.com"}),
            Data(data={"id": 2, "name": "Jane", "email": "jane@example.com"})
        ]
        self.component.validation_mode = "tolerant"
        self.component.check_null_values = True
        self.component.check_duplicates = True

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.validate_data()

        assert isinstance(result, Data)
        assert result.data["summary"]["total_records"] == 2
        assert result.data["summary"]["valid_records"] == 2
        assert result.data["summary"]["invalid_records"] == 0

    def test_validate_data_with_errors_tolerant_mode(self):
        """Test validation with errors in tolerant mode."""
        self.component.data = [
            Data(data={"id": 1, "name": "John", "email": ""}),  # Empty email
            Data(data={"id": "invalid", "name": "Jane", "email": "jane@example.com"})  # Invalid ID type
        ]
        self.component.validation_mode = "tolerant"
        self.component.check_null_values = True
        self.component.check_data_types = True
        self.component.type_schema = '{"id": "integer", "email": "email"}'

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.validate_data()

        assert result.data["summary"]["total_records"] == 2
        assert result.data["summary"]["invalid_records"] == 2
        assert len(result.data["errors"]) > 0

    def test_validate_data_strict_mode_fails_fast(self):
        """Test validation in strict mode fails on first error."""
        self.component.data = [
            Data(data={"id": 1, "name": "John", "email": ""}),  # Empty email - should fail immediately
            Data(data={"id": 2, "name": "Jane", "email": "jane@example.com"})
        ]
        self.component.validation_mode = "strict"
        self.component.check_null_values = True

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            with pytest.raises(ValueError):
                result = self.component.validate_data()
                # In strict mode, should raise an error before completing

    def test_get_clean_data_without_validation(self):
        """Test getting clean data without running validation first."""
        with pytest.raises(ValueError):
            self.component.get_clean_data()

    def test_get_error_records_without_validation(self):
        """Test getting error records without running validation first."""
        with pytest.raises(ValueError):
            self.component.get_error_records()

    def test_auto_clean_functionality(self):
        """Test auto-cleaning of data."""
        valid_records = [{"id": 1, "name": "John"}]
        error_records = [
            {
                "data": {"id": "123", "name": "Jane"},  # String ID that can be converted
                "errors": [{"type": "data_type", "field": "id", "expected_type": "integer"}]
            }
        ]

        cleaned = self.component._perform_auto_clean(valid_records, error_records)

        assert len(cleaned) == 2  # Original valid + cleaned record
        assert cleaned[1]["id"] == 123  # Should be converted to integer

    def test_format_validation_report(self):
        """Test validation report formatting."""
        results = {
            "summary": {
                "total_records": 10,
                "valid_records": 8,
                "invalid_records": 2,
                "validation_timestamp": "2024-01-01T12:00:00",
                "validation_mode": "tolerant"
            },
            "checks_performed": ["null_value_check", "data_type_check"],
            "errors": [
                {"type": "null_value", "field": "email"},
                {"type": "data_type", "field": "id"}
            ],
            "statistics": {
                "data_quality_score": 85.5,
                "field_analysis": {
                    "name": {"null_percentage": 10.0},
                    "email": {"null_percentage": 20.0}
                }
            }
        }

        report = self.component._format_validation_report(results)

        assert "DATA VALIDATION REPORT" in report
        assert "Total Records: 10" in report
        assert "Valid Records: 8" in report
        assert "Success Rate: 80.00%" in report
        assert "Overall Quality Score: 85.50%" in report

    def test_update_build_config(self):
        """Test build config updates based on field changes."""
        build_config = {
            "type_schema": {"show": False},
            "range_schema": {"show": False},
            "custom_rules": {"show": False},
            "null_threshold": {"show": False}
        }

        # Test check_data_types field
        result = self.component.update_build_config(build_config, True, "check_data_types")
        assert result["type_schema"]["show"] is True

        # Test check_ranges field
        result = self.component.update_build_config(build_config, True, "check_ranges")
        assert result["range_schema"]["show"] is True

        # Test use_custom_rules field
        result = self.component.update_build_config(build_config, True, "use_custom_rules")
        assert result["custom_rules"]["show"] is True

        # Test auto_clean field
        result = self.component.update_build_config(build_config, True, "auto_clean")
        assert result["null_threshold"]["show"] is True