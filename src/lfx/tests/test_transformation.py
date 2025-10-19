"""Unit tests for transformation module."""

import pytest

from lfx.base.transformation import BuiltInTransformations, ScriptTransformation, TransformationExecutor


class TestBuiltInTransformations:
    """Test built-in transformation functions."""

    def test_upper(self):
        assert BuiltInTransformations.upper("hello") == "HELLO"
        assert BuiltInTransformations.upper(None) is None
        assert BuiltInTransformations.upper(123) == "123"

    def test_lower(self):
        assert BuiltInTransformations.lower("HELLO") == "hello"
        assert BuiltInTransformations.lower(None) is None
        assert BuiltInTransformations.lower(123) == "123"

    def test_trim(self):
        assert BuiltInTransformations.trim("  hello  ") == "hello"
        assert BuiltInTransformations.trim(None) is None
        assert BuiltInTransformations.trim(123) == "123"

    def test_mask_phone(self):
        assert BuiltInTransformations.mask_phone("13812345678") == "138****5678"
        assert BuiltInTransformations.mask_phone("1234567") == "123****67"
        assert BuiltInTransformations.mask_phone("123") == "123"
        assert BuiltInTransformations.mask_phone(None) is None

    def test_mask_idcard(self):
        assert BuiltInTransformations.mask_idcard("110101199001011234") == "110101********1234"
        assert BuiltInTransformations.mask_idcard("110101900101123") == "110101*****0123"
        assert BuiltInTransformations.mask_idcard("12345") == "12345"
        assert BuiltInTransformations.mask_idcard(None) is None

    def test_mask_email(self):
        assert BuiltInTransformations.mask_email("test@example.com") == "t***t@example.com"
        assert BuiltInTransformations.mask_email("ab@test.com") == "a***b@test.com"
        assert BuiltInTransformations.mask_email("a@test.com") == "a***@test.com"
        assert BuiltInTransformations.mask_email("notanemail") == "notanemail"
        assert BuiltInTransformations.mask_email(None) is None

    def test_mask_name(self):
        assert BuiltInTransformations.mask_name("张三") == "张*"
        assert BuiltInTransformations.mask_name("李四五") == "李*五"
        assert BuiltInTransformations.mask_name("王") == "王"
        assert BuiltInTransformations.mask_name(None) is None

    def test_md5(self):
        assert BuiltInTransformations.md5("hello") == "5d41402abc4b2a76b9719d911017c592"
        assert BuiltInTransformations.md5("") == "d41d8cd98f00b204e9800998ecf8427e"
        assert BuiltInTransformations.md5(None) == ""

    def test_sha256(self):
        assert len(BuiltInTransformations.sha256("hello")) == 64
        assert BuiltInTransformations.sha256(None) == ""

    def test_to_int(self):
        assert BuiltInTransformations.to_int("123") == 123
        assert BuiltInTransformations.to_int("123.45") == 123
        assert BuiltInTransformations.to_int("abc") is None
        assert BuiltInTransformations.to_int(None) is None

    def test_to_float(self):
        assert BuiltInTransformations.to_float("123.45") == 123.45
        assert BuiltInTransformations.to_float("123") == 123.0
        assert BuiltInTransformations.to_float("abc") is None
        assert BuiltInTransformations.to_float(None) is None

    def test_to_str(self):
        assert BuiltInTransformations.to_str(123) == "123"
        assert BuiltInTransformations.to_str(True) == "True"
        assert BuiltInTransformations.to_str(None) == ""

    def test_to_bool(self):
        assert BuiltInTransformations.to_bool("true") is True
        assert BuiltInTransformations.to_bool("yes") is True
        assert BuiltInTransformations.to_bool("1") is True
        assert BuiltInTransformations.to_bool("false") is False
        assert BuiltInTransformations.to_bool("0") is False
        assert BuiltInTransformations.to_bool(None) is False
        assert BuiltInTransformations.to_bool(1) is True
        assert BuiltInTransformations.to_bool(0) is False


class TestScriptTransformation:
    """Test script transformation functions."""

    def test_apply_expression_simple(self):
        result = ScriptTransformation.apply_expression(10, "value * 2", {})
        assert result == 20

    def test_apply_expression_with_variables(self):
        context = {"price": 100, "tax_rate": 0.1}
        result = ScriptTransformation.apply_expression(100, "${price} * (1 + ${tax_rate})", context)
        assert result == "100 * (1 + 0.1)"  # String replacement

    def test_execute_python(self):
        script = """
if value > 10:
    result = value * 2
else:
    result = value
"""
        result = ScriptTransformation.execute_python(15, script, {})
        assert result == 30

        result = ScriptTransformation.execute_python(5, script, {})
        assert result == 5

    def test_execute_javascript_like(self):
        # Test JS-like ternary operator conversion
        script = "value > 10 ? value * 2 : value"
        # Since we're using Python eval, this tests the conversion logic
        result = ScriptTransformation.execute_javascript(15, script, {})
        assert result == 30

        result = ScriptTransformation.execute_javascript(5, script, {})
        assert result == 5


class TestTransformationExecutor:
    """Test transformation executor."""

    def setup_method(self):
        self.executor = TransformationExecutor()

    def test_transform_row_simple(self):
        row_data = {"name": "john doe", "age": "25", "email": "john@example.com"}

        field_mappings = [
            {
                "source_field": "name",
                "target_field": "full_name",
                "transformation_rule": "upper",
                "data_type": "string",
                "enabled": True,
            },
            {
                "source_field": "age",
                "target_field": "user_age",
                "transformation_rule": "to_int",
                "data_type": "integer",
                "enabled": True,
            },
            {
                "source_field": "email",
                "target_field": "masked_email",
                "transformation_rule": "mask_email",
                "data_type": "string",
                "enabled": True,
            },
        ]

        result = self.executor.transform_row(row_data, field_mappings)

        assert result["full_name"] == "JOHN DOE"
        assert result["user_age"] == 25
        assert result["masked_email"] == "j***n@example.com"

    def test_transform_row_with_default_value(self):
        row_data = {"name": "john"}

        field_mappings = [
            {"source_field": "name", "target_field": "name", "enabled": True},
            {"source_field": "status", "target_field": "status", "default_value": "active", "enabled": True},
        ]

        result = self.executor.transform_row(row_data, field_mappings)

        assert result["name"] == "john"
        assert result["status"] == "active"

    def test_transform_row_disabled_mapping(self):
        row_data = {"name": "john", "age": "25"}

        field_mappings = [
            {"source_field": "name", "target_field": "name", "transformation_rule": "upper", "enabled": True},
            {
                "source_field": "age",
                "target_field": "age",
                "transformation_rule": "to_int",
                "enabled": False,  # Disabled
            },
        ]

        result = self.executor.transform_row(row_data, field_mappings)

        assert result["name"] == "JOHN"
        assert "age" not in result or result["age"] == "25"

    def test_transform_row_with_complex_rule(self):
        row_data = {"price": 100, "quantity": 2}

        field_mappings = [
            {
                "source_field": "price",
                "target_field": "total",
                "transformation_rule": {"type": "python", "content": "result = value * row.get('quantity', 1)"},
                "enabled": True,
            }
        ]

        result = self.executor.transform_row(row_data, field_mappings)

        assert result["total"] == 200

    def test_apply_transformation_builtin(self):
        result = self.executor.apply_transformation("hello", "upper", {})
        assert result == "HELLO"

    def test_apply_transformation_expression(self):
        result = self.executor.apply_transformation(10, "value * 2 + 5", {})
        assert result == 25

    def test_apply_transformation_dict_rule(self):
        rule = {"type": "builtin", "function": "upper"}
        result = self.executor.apply_transformation("hello", rule, {})
        assert result == "HELLO"

    def test_convert_type(self):
        assert self.executor.convert_type("123", "integer") == 123
        assert self.executor.convert_type("123.45", "float") == 123.45
        assert self.executor.convert_type(123, "string") == "123"
        assert self.executor.convert_type("true", "boolean") is True
        assert self.executor.convert_type(None, "string") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
