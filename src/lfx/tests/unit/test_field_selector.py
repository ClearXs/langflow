import pytest
import json
from lfx.components.data.field_selector import FieldSelectorComponent
from langflow.schema import Data


class TestFieldSelectorComponent:

    @pytest.fixture
    def component(self):
        return FieldSelectorComponent()

    @pytest.fixture
    def sample_data(self):
        return [
            Data(data={
                "id": 1,
                "name": "John",
                "email": "john@example.com",
                "age": 25,
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "zip": "10001"
                },
                "tags": ["user", "admin"]
            }),
            Data(data={
                "id": 2,
                "name": "Jane",
                "email": "jane@example.com",
                "age": 30,
                "phone": "555-1234",
                "address": {
                    "street": "456 Oak Ave",
                    "city": "Boston",
                    "zip": "02101"
                }
            }),
            Data(data={
                "id": 3,
                "name": "",
                "email": None,
                "age": 35,
                "status": "active"
            })
        ]

    def test_include_strategy(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email"]'

        result = component.select_fields()

        for item in result.data:
            assert set(item.data.keys()) == {"id", "name", "email"}

        assert result.data[0].data["id"] == 1
        assert result.data[0].data["name"] == "John"
        assert result.data[0].data["email"] == "john@example.com"

    def test_exclude_strategy(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "exclude"
        component.field_list = '["address", "tags", "phone"]'

        result = component.select_fields()

        # Address, tags, and phone should be excluded
        for item in result.data:
            assert "address" not in item.data
            assert "tags" not in item.data
            assert "phone" not in item.data

        # Other fields should remain
        assert "id" in result.data[0].data
        assert "name" in result.data[0].data
        assert "email" in result.data[0].data

    def test_regex_strategy(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "regex"
        component.field_patterns = '["^(id|name)$", "email"]'

        result = component.select_fields()

        # Should include fields matching the regex patterns
        for item in result.data:
            for field in item.data.keys():
                assert field in ["id", "name", "email"]

    def test_conditional_strategy(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "conditional"
        component.selection_conditions = '{"non_empty": true, "exclude_null": true}'

        result = component.select_fields()

        # Should exclude empty strings and null values
        for item in result.data:
            for value in item.data.values():
                if isinstance(value, str):
                    assert value != ""
                assert value is not None

    def test_field_mapping_rename(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email"]'
        component.field_mapping = '{"id": "user_id", "name": "full_name"}'

        result = component.select_fields()

        # Fields should be renamed according to mapping
        for item in result.data:
            assert "user_id" in item.data
            assert "full_name" in item.data
            assert "email" in item.data  # Not renamed
            assert "id" not in item.data
            assert "name" not in item.data

        assert result.data[0].data["user_id"] == 1
        assert result.data[0].data["full_name"] == "John"

    def test_default_values(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email", "phone", "status"]'
        component.default_values = '{"phone": "N/A", "status": "unknown"}'

        result = component.select_fields()

        # Missing fields should get default values
        assert result.data[0].data["phone"] == "N/A"  # Not in original data
        assert result.data[0].data["status"] == "unknown"  # Not in original data
        assert result.data[1].data["phone"] == "555-1234"  # Original value preserved
        assert result.data[2].data["status"] == "active"  # Original value preserved

    def test_flatten_nested(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "address"]'
        component.flatten_nested = True

        result = component.select_fields()

        # Nested address fields should be flattened
        assert "address.street" in result.data[0].data
        assert "address.city" in result.data[0].data
        assert "address.zip" in result.data[0].data
        assert result.data[0].data["address.street"] == "123 Main St"

    def test_preserve_structure(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "address"]'
        component.preserve_structure = True
        component.flatten_nested = False

        result = component.select_fields()

        # Nested structure should be preserved
        assert isinstance(result.data[0].data["address"], dict)
        assert result.data[0].data["address"]["street"] == "123 Main St"

    def test_case_sensitivity(self, component):
        case_data = [
            Data(data={"ID": 1, "Name": "John", "EMAIL": "john@example.com"})
        ]

        component.data = case_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email"]'
        component.case_sensitive = False

        result = component.select_fields()

        # Should match fields regardless of case
        assert len(result.data[0].data) == 3

    def test_include_empty_fields(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email"]'
        component.include_empty = False

        result = component.select_fields()

        # Empty/null fields should be excluded
        for item in result.data:
            for value in item.data.values():
                if isinstance(value, str):
                    assert value != ""
                assert value is not None

    def test_max_depth(self, component):
        deep_nested_data = [
            Data(data={
                "level1": {
                    "level2": {
                        "level3": {
                            "deep_value": "found"
                        },
                        "value2": "level2"
                    },
                    "value1": "level1"
                }
            })
        ]

        component.data = deep_nested_data
        component.selection_strategy = "include"
        component.field_list = '["level1"]'
        component.flatten_nested = True
        component.max_depth = 2

        result = component.select_fields()

        # Should only flatten to max depth of 2
        flattened_keys = list(result.data[0].data.keys())
        assert any("level1.level2" in key for key in flattened_keys)
        # Should not flatten level3 due to max_depth
        assert not any("level1.level2.level3" in key for key in flattened_keys)

    def test_strict_mode_missing_field(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "nonexistent_field"]'
        component.strict_mode = True

        with pytest.raises(ValueError, match="Required field"):
            component.select_fields()

    def test_selection_report(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name", "email"]'

        # Run selection first
        component.select_fields()

        # Get selection report
        report = component.get_selection_report()

        assert "total_records" in report.data
        assert "selected_fields" in report.data
        assert "excluded_fields" in report.data
        assert "records_processed" in report.data

        assert report.data["total_records"] == 3
        assert report.data["records_processed"] == 3

    def test_excluded_fields_output(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "exclude"
        component.field_list = '["address", "tags"]'

        # Run selection first
        component.select_fields()

        # Get excluded fields
        excluded = component.get_excluded_fields()

        assert "excluded_field_names" in excluded.data
        assert "address" in excluded.data["excluded_field_names"]
        assert "tags" in excluded.data["excluded_field_names"]

    def test_empty_data_handling(self, component):
        component.data = []

        with pytest.raises(ValueError, match="empty"):
            component.select_fields()

    def test_invalid_json_field_list(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = "invalid json"

        with pytest.raises(json.JSONDecodeError):
            component.select_fields()

    def test_invalid_regex_pattern(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "regex"
        component.field_patterns = '["[invalid"]'

        with pytest.raises(Exception):  # Should raise regex error
            component.select_fields()

    def test_single_record(self, component):
        single_data = [Data(data={"id": 1, "name": "John", "email": "john@example.com"})]
        component.data = single_data
        component.selection_strategy = "include"
        component.field_list = '["id", "name"]'

        result = component.select_fields()

        assert len(result.data) == 1
        assert set(result.data[0].data.keys()) == {"id", "name"}

    def test_no_matching_fields(self, component, sample_data):
        component.data = sample_data
        component.selection_strategy = "include"
        component.field_list = '["nonexistent1", "nonexistent2"]'
        component.strict_mode = False

        result = component.select_fields()

        # Should return empty records when no fields match
        for item in result.data:
            assert len(item.data) == 0

    def test_all_fields_excluded(self, component, sample_data):
        # Get all field names from first record
        all_fields = list(sample_data[0].data.keys())

        component.data = sample_data
        component.selection_strategy = "exclude"
        component.field_list = json.dumps(all_fields)

        result = component.select_fields()

        # Should return empty records when all fields are excluded
        for item in result.data:
            assert len(item.data) == 0