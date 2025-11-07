"""Tests for ETLFieldTypeConversion component."""

from datetime import datetime

import pytest

from lfx.components.manipulations.field_type_conversion import ETLFieldTypeConversion
from lfx.schema import Data


class TestETLFieldTypeConversion:
    """Test suite for field type conversion component."""

    def test_component_initialization(self):
        """Test that component initializes correctly."""
        component = ETLFieldTypeConversion()
        # i18n may not be loaded in test environment, check for key or translated value
        assert "field_type_conversion" in component.display_name or component.display_name == "字段类型转换"
        assert component.name == "ETLFieldTypeConversion"
        assert component.icon == "type"

    def test_convert_string_to_integer(self):
        """Test string to integer conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"age": "30", "score": "95"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
                {"field_name": "score", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["age"] == 30
        assert result[0].data["score"] == 95
        assert isinstance(result[0].data["age"], int)
        assert isinstance(result[0].data["score"], int)

    def test_convert_string_to_float(self):
        """Test string to float conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"price": "99.99", "rate": "0.85"})],
            type_conversions=[
                {"field_name": "price", "source_type": "string", "target_type": "float", "conversion_rule": ""},
                {"field_name": "rate", "source_type": "string", "target_type": "float", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["price"] == 99.99
        assert result[0].data["rate"] == 0.85
        assert isinstance(result[0].data["price"], float)

    def test_convert_string_to_boolean(self):
        """Test string to boolean conversion."""
        test_data = [
            Data(data={"active": "true", "verified": "1", "enabled": "yes"}),
            Data(data={"active": "false", "verified": "0", "enabled": "no"}),
        ]

        component = ETLFieldTypeConversion(
            data_input=test_data,
            type_conversions=[
                {"field_name": "active", "source_type": "string", "target_type": "boolean", "conversion_rule": ""},
                {"field_name": "verified", "source_type": "string", "target_type": "boolean", "conversion_rule": ""},
                {"field_name": "enabled", "source_type": "string", "target_type": "boolean", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 2
        # First row
        assert result[0].data["active"] is True
        assert result[0].data["verified"] is True
        assert result[0].data["enabled"] is True
        # Second row
        assert result[1].data["active"] is False
        assert result[1].data["verified"] is False
        assert result[1].data["enabled"] is False

    def test_convert_string_to_datetime(self):
        """Test string to datetime conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"date": "2024-01-15", "timestamp": "2024-01-15 10:30:00"})],
            type_conversions=[
                {
                    "field_name": "date",
                    "source_type": "string",
                    "target_type": "datetime",
                    "conversion_rule": "yyyy-MM-dd",
                },
                {
                    "field_name": "timestamp",
                    "source_type": "string",
                    "target_type": "datetime",
                    "conversion_rule": "yyyy-MM-dd HH:mm:ss",
                },
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["date"] == "2024-01-15"
        assert result[0].data["timestamp"] == "2024-01-15 10:30:00"

    def test_convert_float_to_integer(self):
        """Test float to integer conversion (with precision loss)."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"value": 3.14, "amount": 99.99})],
            type_conversions=[
                {"field_name": "value", "source_type": "float", "target_type": "integer", "conversion_rule": ""},
                {"field_name": "amount", "source_type": "float", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["value"] == 3
        assert result[0].data["amount"] == 99

    def test_convert_integer_to_float(self):
        """Test integer to float conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"count": 42, "total": 100})],
            type_conversions=[
                {"field_name": "count", "source_type": "integer", "target_type": "float", "conversion_rule": ""},
                {"field_name": "total", "source_type": "integer", "target_type": "float", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["count"] == 42.0
        assert result[0].data["total"] == 100.0
        assert isinstance(result[0].data["count"], float)

    def test_convert_to_string(self):
        """Test converting various types to string."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"age": 30, "price": 99.99, "active": True})],
            type_conversions=[
                {"field_name": "age", "source_type": "integer", "target_type": "string", "conversion_rule": ""},
                {"field_name": "price", "source_type": "float", "target_type": "string", "conversion_rule": ""},
                {"field_name": "active", "source_type": "boolean", "target_type": "string", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["age"] == "30"
        assert result[0].data["price"] == "99.99"
        assert result[0].data["active"] == "True"

    def test_pass_through_unmapped_fields(self):
        """Test that unmapped fields are passed through."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"name": "张三", "age": "30", "city": "北京"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=True,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["name"] == "张三"  # Passed through
        assert result[0].data["age"] == 30  # Converted
        assert result[0].data["city"] == "北京"  # Passed through

    def test_no_pass_through_unmapped_fields(self):
        """Test that unmapped fields are not passed through when disabled."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"name": "张三", "age": "30", "city": "北京"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert "name" not in result[0].data
        assert result[0].data["age"] == 30
        assert "city" not in result[0].data

    def test_strict_validation_mode(self):
        """Test that strict validation mode raises errors on conversion failure."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"age": "abc"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        with pytest.raises(ValueError) as exc_info:
            component.convert_types()
        error_msg = str(exc_info.value)
        # i18n may not be loaded, check for error message presence
        # Either contains "field_conversion_failed" key or actual error message
        assert "field_conversion_failed" in error_msg or ("row" in error_msg.lower() and "age" in error_msg.lower())

    def test_non_strict_validation_mode(self):
        """Test that non-strict validation mode keeps original value on error."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"age": "abc", "score": "95"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
                {"field_name": "score", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=False,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["age"] == "abc"  # Kept original value
        assert result[0].data["score"] == 95  # Converted successfully

    def test_null_value_handling(self):
        """Test that null values are preserved."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"age": None, "score": "", "name": "test"})],
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
                {"field_name": "score", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=True,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["age"] is None
        assert result[0].data["score"] is None
        assert result[0].data["name"] == "test"

    def test_custom_boolean_conversion_rule(self):
        """Test custom boolean conversion rules."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"status": "active", "flag": "inactive"})],
            type_conversions=[
                {
                    "field_name": "status",
                    "source_type": "string",
                    "target_type": "boolean",
                    "conversion_rule": "active,enabled,on",
                },
                {
                    "field_name": "flag",
                    "source_type": "string",
                    "target_type": "boolean",
                    "conversion_rule": "active,enabled,on",
                },
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["status"] is True  # "active" in rule
        assert result[0].data["flag"] is False  # "inactive" not in rule

    def test_multiple_rows_conversion(self):
        """Test conversion of multiple rows."""
        test_data = [
            Data(data={"name": "张三", "age": "30", "salary": "5000.5"}),
            Data(data={"name": "李四", "age": "25", "salary": "6000.0"}),
            Data(data={"name": "王五", "age": "35", "salary": "7500.75"}),
        ]

        component = ETLFieldTypeConversion(
            data_input=test_data,
            type_conversions=[
                {"field_name": "age", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
                {"field_name": "salary", "source_type": "string", "target_type": "float", "conversion_rule": ""},
            ],
            pass_through_unmapped=True,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 3
        assert all(isinstance(row.data["age"], int) for row in result)
        assert all(isinstance(row.data["salary"], float) for row in result)
        assert result[0].data["name"] == "张三"
        assert result[1].data["age"] == 25
        assert result[2].data["salary"] == 7500.75

    def test_infer_type_string(self):
        """Test type inference for strings."""
        component = ETLFieldTypeConversion()
        assert component._infer_type("hello") == "string"
        assert component._infer_type("world 123") == "string"

    def test_infer_type_integer(self):
        """Test type inference for integers."""
        component = ETLFieldTypeConversion()
        assert component._infer_type(42) == "integer"
        assert component._infer_type("123") == "integer"
        assert component._infer_type("-456") == "integer"

    def test_infer_type_float(self):
        """Test type inference for floats."""
        component = ETLFieldTypeConversion()
        assert component._infer_type(3.14) == "float"
        assert component._infer_type("99.99") == "float"
        assert component._infer_type("-0.5") == "float"

    def test_infer_type_boolean(self):
        """Test type inference for booleans."""
        component = ETLFieldTypeConversion()
        assert component._infer_type(True) == "boolean"
        assert component._infer_type(False) == "boolean"
        assert component._infer_type("true") == "boolean"
        assert component._infer_type("false") == "boolean"
        assert component._infer_type("yes") == "boolean"
        assert component._infer_type("no") == "boolean"

    def test_infer_type_datetime(self):
        """Test type inference for datetime."""
        component = ETLFieldTypeConversion()
        assert component._infer_type(datetime(2024, 1, 15)) == "datetime"
        assert component._infer_type("2024-01-15") == "datetime"
        assert component._infer_type("2024-01-15 10:30:00") == "datetime"

    def test_merge_types(self):
        """Test type merging logic."""
        component = ETLFieldTypeConversion()
        # Integer + Float = Float (wider type)
        assert component._merge_types("integer", "float") == "float"
        # Boolean + Integer = Integer (wider type)
        assert component._merge_types("boolean", "integer") == "integer"
        # Datetime + String = String (widest type)
        assert component._merge_types("datetime", "string") == "string"
        # Same types
        assert component._merge_types("integer", "integer") == "integer"

    def test_check_data_loss_warning_float_to_int(self):
        """Test data loss warning for float to integer."""
        component = ETLFieldTypeConversion()
        warning = component._check_data_loss_warning("float", "integer")
        assert "小数精度" in warning or "decimal" in warning.lower()

    def test_check_data_loss_warning_string_to_number(self):
        """Test data loss warning for string to number."""
        component = ETLFieldTypeConversion()
        warning = component._check_data_loss_warning("string", "integer")
        assert "解析失败" in warning or "parse" in warning.lower()

    def test_check_data_loss_warning_datetime_to_string(self):
        """Test data loss warning for datetime to string."""
        component = ETLFieldTypeConversion()
        warning = component._check_data_loss_warning("datetime", "string")
        assert "时区" in warning or "timezone" in warning.lower()

    def test_check_data_loss_warning_any_to_boolean(self):
        """Test data loss warning for any type to boolean."""
        component = ETLFieldTypeConversion()
        warning = component._check_data_loss_warning("integer", "boolean")
        assert "信息丢失" in warning or "information" in warning.lower()

    def test_parse_datetime_format(self):
        """Test datetime format parsing."""
        component = ETLFieldTypeConversion()
        assert component._parse_datetime_format("yyyy-MM-dd") == "%Y-%m-%d"
        assert component._parse_datetime_format("yyyy-MM-dd HH:mm:ss") == "%Y-%m-%d %H:%M:%S"
        assert component._parse_datetime_format("ISO8601") == "%Y-%m-%dT%H:%M:%S"
        # Unknown format passes through
        assert component._parse_datetime_format("%Y/%m/%d") == "%Y/%m/%d"

    def test_no_input_data_error(self):
        """Test error when no input data is provided."""
        component = ETLFieldTypeConversion(
            data_input=[],
            type_conversions=[],
            pass_through_unmapped=True,
            strict_validation=True,
        )

        with pytest.raises(ValueError) as exc_info:
            component.convert_types()
        assert "输入数据" in str(exc_info.value) or "input" in str(exc_info.value).lower()

    def test_datetime_object_conversion_with_format(self):
        """Test datetime object conversion with custom format."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"timestamp": dt})],
            type_conversions=[
                {
                    "field_name": "timestamp",
                    "source_type": "datetime",
                    "target_type": "datetime",
                    "conversion_rule": "yyyy-MM-dd",
                },
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["timestamp"] == "2024-01-15"

    def test_analyze_field_types(self):
        """Test field type analysis from sample data."""
        test_data = [
            Data(data={"name": "张三", "age": 30, "price": 99.99, "active": True}),
            Data(data={"name": "李四", "age": 25, "price": 150.0, "active": False}),
        ]

        component = ETLFieldTypeConversion()
        field_types = component._analyze_field_types(test_data)

        assert field_types["name"] == "string"
        assert field_types["age"] == "integer"
        assert field_types["price"] == "float"
        assert field_types["active"] == "boolean"

    def test_analyze_field_types_with_mixed_types(self):
        """Test field type analysis with mixed types (should use widest type)."""
        test_data = [
            Data(data={"value": 10}),  # integer
            Data(data={"value": 10.5}),  # float
        ]

        component = ETLFieldTypeConversion()
        field_types = component._analyze_field_types(test_data)

        assert field_types["value"] == "float"  # Widest type

    def test_edge_case_empty_string_to_boolean(self):
        """Test edge case: empty string to boolean conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"flag": ""})],
            type_conversions=[
                {"field_name": "flag", "source_type": "string", "target_type": "boolean", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        # Empty string is treated as None, not False
        assert result[0].data["flag"] is None

    def test_edge_case_string_with_decimal_to_integer(self):
        """Test edge case: string with decimal to integer conversion."""
        component = ETLFieldTypeConversion(
            data_input=[Data(data={"value": "42.7"})],
            type_conversions=[
                {"field_name": "value", "source_type": "string", "target_type": "integer", "conversion_rule": ""},
            ],
            pass_through_unmapped=False,
            strict_validation=True,
        )

        result = component.convert_types()
        assert len(result) == 1
        assert result[0].data["value"] == 42  # Truncated
