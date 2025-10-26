"""Unit tests for ETLDataCleaningComponent."""

import pytest

from lfx.components.manipulations.data_cleaning import ETLDataCleaningComponent
from lfx.schema import Data


class TestETLDataCleaningComponent:
    """Test cases for ETL Data Cleaning Component."""

    def test_basic_cleaning_trim(self):
        """Test basic data cleaning with trim transformation."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "  John  ", "age": "25"}),
                Data(data={"name": "  Jane  ", "age": "30"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "trim", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 2
        assert result[0].data["name"] == "John"
        assert result[1].data["name"] == "Jane"

    def test_basic_cleaning_upper(self):
        """Test data cleaning with uppercase transformation."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "john", "city": "beijing"}),
                Data(data={"name": "jane", "city": "shanghai"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
                {"field_name": "city", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 2
        assert result[0].data["name"] == "JOHN"
        assert result[0].data["city"] == "BEIJING"
        assert result[1].data["name"] == "JANE"
        assert result[1].data["city"] == "SHANGHAI"

    def test_mask_phone(self):
        """Test phone number masking."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"phone": "13812345678", "name": "John"}),
                Data(data={"phone": "13987654321", "name": "Jane"}),
            ],
            cleaning_rules=[
                {"field_name": "phone", "transformation_rule": "mask_phone", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 2
        assert result[0].data["phone"] == "138****5678"
        assert result[1].data["phone"] == "139****4321"
        # Name should remain unchanged
        assert result[0].data["name"] == "John"

    def test_mask_email(self):
        """Test email address masking."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"email": "test@example.com", "user": "test"}),
                Data(data={"email": "admin@company.org", "user": "admin"}),
            ],
            cleaning_rules=[
                {"field_name": "email", "transformation_rule": "mask_email", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 2
        assert result[0].data["email"] == "t***t@example.com"
        assert result[1].data["email"] == "a***n@company.org"

    def test_mask_idcard(self):
        """Test ID card masking."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"idcard": "110101199001011234", "name": "Zhang San"}),
            ],
            cleaning_rules=[
                {"field_name": "idcard", "transformation_rule": "mask_idcard", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        assert result[0].data["idcard"] == "110101********1234"

    def test_filter_conditions_single(self):
        """Test filter conditions with single condition."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "john", "age": 25}),
                Data(data={"name": "jane", "age": 30}),
                Data(data={"name": "bob", "age": 20}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[{"field_name": "age", "operator": ">=", "compare_value": "25", "logic_operator": "AND"}],
            max_records=0,
        )
        result = component.clean_data()

        # Only records matching filter (age >= 25) are output and transformed
        assert len(result) == 2
        assert result[0].data["name"] == "JOHN"
        assert result[1].data["name"] == "JANE"

    def test_filter_conditions_multiple_and(self):
        """Test filter conditions with multiple AND conditions."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "john", "age": 25, "city": "beijing"}),
                Data(data={"name": "jane", "age": 30, "city": "shanghai"}),
                Data(data={"name": "bob", "age": 30, "city": "beijing"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[
                {"field_name": "age", "operator": ">=", "compare_value": "30", "logic_operator": "AND"},
                {"field_name": "city", "operator": "=", "compare_value": "beijing", "logic_operator": "AND"},
            ],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        # Only Bob matches both conditions (age>=30 AND city=beijing), others filtered out
        assert result[0].data["name"] == "BOB"
        assert result[0].data["age"] == 30
        assert result[0].data["city"] == "beijing"

    def test_filter_conditions_multiple_or(self):
        """Test filter conditions with OR logic."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "john", "age": 25, "city": "beijing"}),
                Data(data={"name": "jane", "age": 30, "city": "shanghai"}),
                Data(data={"name": "bob", "age": 20, "city": "guangzhou"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[
                {"field_name": "age", "operator": ">=", "compare_value": "30", "logic_operator": "OR"},
                {"field_name": "city", "operator": "=", "compare_value": "beijing", "logic_operator": "OR"},
            ],
            max_records=0,
        )
        result = component.clean_data()

        # John (city=beijing) and Jane (age>=30) match the OR condition
        assert len(result) == 2
        assert result[0].data["name"] == "JOHN"  # city=beijing
        assert result[1].data["name"] == "JANE"  # age>=30

    def test_max_records(self):
        """Test max records limitation."""
        component = ETLDataCleaningComponent(
            data_input=[Data(data={"value": f"item_{i}"}) for i in range(10)],
            cleaning_rules=[
                {"field_name": "value", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=5,
        )
        result = component.clean_data()

        # max_records limits how many records are processed and output
        assert len(result) == 5
        # All 5 should be transformed to uppercase
        for i in range(5):
            assert result[i].data["value"].startswith("ITEM_")

    def test_type_conversion_to_int(self):
        """Test type conversion to integer."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"price": "100", "count": "5"}),
                Data(data={"price": "200", "count": "10"}),
            ],
            cleaning_rules=[
                {"field_name": "price", "transformation_rule": "to_int", "custom_expression": ""},
                {"field_name": "count", "transformation_rule": "to_int", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 2
        assert result[0].data["price"] == 100
        assert result[0].data["count"] == 5
        assert result[1].data["price"] == 200
        assert result[1].data["count"] == 10

    def test_type_conversion_to_float(self):
        """Test type conversion to float."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"price": "100", "discount": "0.9"}),
            ],
            cleaning_rules=[
                {"field_name": "price", "transformation_rule": "to_float", "custom_expression": ""},
                {"field_name": "discount", "transformation_rule": "to_float", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        assert result[0].data["price"] == 100.0
        assert result[0].data["discount"] == 0.9

    def test_md5_hash(self):
        """Test MD5 hashing."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"password": "secret123", "user": "admin"}),
            ],
            cleaning_rules=[
                {"field_name": "password", "transformation_rule": "md5", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        # MD5 hash should be 32 characters
        assert len(result[0].data["password"]) == 32
        # User should remain unchanged
        assert result[0].data["user"] == "admin"

    def test_multiple_transformations(self):
        """Test multiple transformation rules on different fields."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "  john  ", "email": "test@example.com", "phone": "13812345678"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "trim", "custom_expression": ""},
                {"field_name": "email", "transformation_rule": "mask_email", "custom_expression": ""},
                {"field_name": "phone", "transformation_rule": "mask_phone", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        assert result[0].data["name"] == "john"
        assert result[0].data["email"] == "t***t@example.com"
        assert result[0].data["phone"] == "138****5678"

    def test_no_transformation_with_none_rule(self):
        """Test that 'none' transformation rule doesn't change data."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "John", "age": 25}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "none", "custom_expression": ""},
                {"field_name": "age", "transformation_rule": "none", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )
        result = component.clean_data()

        assert len(result) == 1
        assert result[0].data["name"] == "John"
        assert result[0].data["age"] == 25

    def test_string_operators_contains(self):
        """Test contains operator in filter conditions."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"description": "This is a test", "value": 1}),
                Data(data={"description": "Another example", "value": 2}),
            ],
            cleaning_rules=[
                {"field_name": "value", "transformation_rule": "to_str", "custom_expression": ""},
            ],
            filter_conditions=[
                {"field_name": "description", "operator": "contains", "compare_value": "test", "logic_operator": "AND"}
            ],
            max_records=0,
        )
        result = component.clean_data()

        # Only records matching filter (contains "test") are output and transformed
        assert len(result) == 1
        assert result[0].data["value"] == "1"  # Transformed (contains "test")

    def test_string_operators_starts_with(self):
        """Test starts_with operator."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"code": "BJ001", "name": "Item 1"}),
                Data(data={"code": "SH002", "name": "Item 2"}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[
                {"field_name": "code", "operator": "starts_with", "compare_value": "BJ", "logic_operator": "AND"}
            ],
            max_records=0,
        )
        result = component.clean_data()

        # Only records matching filter (starts with "BJ") are output and transformed
        assert len(result) == 1
        assert result[0].data["name"] == "ITEM 1"  # Starts with BJ

    def test_empty_data_input(self):
        """Test handling of empty data input."""
        component = ETLDataCleaningComponent(
            data_input=[],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )

        with pytest.raises(ValueError):
            component.clean_data()

    def test_no_cleaning_rules(self):
        """Test error when no cleaning rules are provided."""
        component = ETLDataCleaningComponent(
            data_input=[Data(data={"name": "John"})],
            cleaning_rules=[],
            filter_conditions=[],
            max_records=0,
        )

        with pytest.raises(ValueError):
            component.clean_data()

    def test_nonexistent_field_in_rule(self):
        """Test handling of nonexistent field in cleaning rule."""
        component = ETLDataCleaningComponent(
            data_input=[Data(data={"name": "John", "age": 25})],
            cleaning_rules=[
                {"field_name": "nonexistent_field", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[],
            max_records=0,
        )

        # Should not raise error, just skip the nonexistent field
        result = component.clean_data()
        assert len(result) == 1
        assert result[0].data["name"] == "John"  # Unchanged

    def test_mixed_filter_and_max_records(self):
        """Test combination of filter conditions and max records."""
        component = ETLDataCleaningComponent(
            data_input=[
                Data(data={"name": "john", "age": 25}),
                Data(data={"name": "jane", "age": 30}),
                Data(data={"name": "bob", "age": 35}),
                Data(data={"name": "alice", "age": 40}),
            ],
            cleaning_rules=[
                {"field_name": "name", "transformation_rule": "upper", "custom_expression": ""},
            ],
            filter_conditions=[{"field_name": "age", "operator": ">=", "compare_value": "30", "logic_operator": "AND"}],
            max_records=2,  # Only transform first 2 matching records
        )
        result = component.clean_data()

        # Only 2 records match filter (age>=30) and are transformed
        assert len(result) == 2
        assert result[0].data["name"] == "JANE"  # Matches filter, transformed (1st)
        assert result[1].data["name"] == "BOB"  # Matches filter, transformed (2nd)
