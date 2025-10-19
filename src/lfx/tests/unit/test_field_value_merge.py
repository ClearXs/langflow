"""Unit tests for ETLFieldValueMergeComponent"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock

from lfx.components.manipulations.field_value_merge import ETLFieldValueMergeComponent
from lfx.schema import Data


class TestETLFieldValueMergeComponent:
    """Test suite for Field Value Merge component"""

    @pytest.fixture
    def component(self):
        """Create a component instance"""
        return ETLFieldValueMergeComponent()

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing"""
        return [
            Data(data={"first_name": "John", "last_name": "Doe", "age": 30, "salary": 5000.50}),
            Data(data={"first_name": "Jane", "last_name": "Smith", "age": 25, "salary": 6000.75}),
            Data(data={"first_name": "Bob", "last_name": "Johnson", "age": 35, "salary": 7000.25}),
        ]

    def test_basic_string_merge(self, component, sample_data):
        """Test basic string concatenation (A LINK B)"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = False

        result = component.merge_field_values()

        assert len(result) == 3
        assert result[0].data["full_name"] == "John Doe"
        assert result[1].data["full_name"] == "Jane Smith"
        assert result[2].data["full_name"] == "Bob Johnson"
        # Original fields should still exist
        assert "first_name" in result[0].data
        assert "last_name" in result[0].data

    def test_string_merge_with_custom_separator(self, component, sample_data):
        """Test string merge with custom separator"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": "_",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = False

        result = component.merge_field_values()

        assert result[0].data["full_name"] == "John_Doe"
        assert result[1].data["full_name"] == "Jane_Smith"

    def test_addition_operation(self, component, sample_data):
        """Test addition operation (A + B)"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "total",
                "operation": "A + B",
                "field_a": "age",
                "field_b": "salary",
                "separator": "",
                "value_type": "float",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert result[0].data["total"] == pytest.approx(5030.50, rel=1e-2)
        assert result[1].data["total"] == pytest.approx(6025.75, rel=1e-2)

    def test_subtraction_operation(self, component, sample_data):
        """Test subtraction operation (A - B)"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "difference",
                "operation": "A - B",
                "field_a": "salary",
                "field_b": "age",
                "separator": "",
                "value_type": "float",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert result[0].data["difference"] == pytest.approx(4970.50, rel=1e-2)
        assert result[1].data["difference"] == pytest.approx(5975.75, rel=1e-2)

    def test_multiplication_operation(self, component, sample_data):
        """Test multiplication operation (A * B)"""
        component.data_input = [
            Data(data={"quantity": 10, "price": 5.5}),
            Data(data={"quantity": 20, "price": 3.25}),
        ]
        component.merge_configs = [
            {
                "new_field": "total_price",
                "operation": "A * B",
                "field_a": "quantity",
                "field_b": "price",
                "separator": "",
                "value_type": "float",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert result[0].data["total_price"] == pytest.approx(55.0, rel=1e-2)
        assert result[1].data["total_price"] == pytest.approx(65.0, rel=1e-2)

    def test_division_operation(self, component, sample_data):
        """Test division operation (A / B)"""
        component.data_input = [
            Data(data={"total": 100, "count": 4}),
            Data(data={"total": 150, "count": 5}),
        ]
        component.merge_configs = [
            {
                "new_field": "average",
                "operation": "A / B",
                "field_a": "total",
                "field_b": "count",
                "separator": "",
                "value_type": "float",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert result[0].data["average"] == pytest.approx(25.0, rel=1e-2)
        assert result[1].data["average"] == pytest.approx(30.0, rel=1e-2)

    def test_modulo_operation(self, component, sample_data):
        """Test modulo operation (A % B)"""
        component.data_input = [
            Data(data={"number": 17, "divisor": 5}),
            Data(data={"number": 23, "divisor": 7}),
        ]
        component.merge_configs = [
            {
                "new_field": "remainder",
                "operation": "A % B",
                "field_a": "number",
                "field_b": "divisor",
                "separator": "",
                "value_type": "integer",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert result[0].data["remainder"] == 2
        assert result[1].data["remainder"] == 2

    def test_type_conversion_integer(self, component):
        """Test type conversion to integer"""
        component.data_input = [
            Data(data={"a": 10.7, "b": 5.3}),
        ]
        component.merge_configs = [
            {
                "new_field": "sum",
                "operation": "A + B",
                "field_a": "a",
                "field_b": "b",
                "separator": "",
                "value_type": "integer",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert isinstance(result[0].data["sum"], (int, pd.Int64Dtype))
        assert result[0].data["sum"] == 16

    def test_type_conversion_float(self, component):
        """Test type conversion to float with precision"""
        component.data_input = [
            Data(data={"a": 10, "b": 3}),
        ]
        component.merge_configs = [
            {
                "new_field": "division",
                "operation": "A / B",
                "field_a": "a",
                "field_b": "b",
                "separator": "",
                "value_type": "float",
            }
        ]
        component.drop_source_fields = False
        component.decimal_precision = 3

        result = component.merge_field_values()

        assert isinstance(result[0].data["division"], float)
        assert result[0].data["division"] == pytest.approx(3.333, rel=1e-3)

    def test_drop_source_fields(self, component, sample_data):
        """Test dropping source fields after merge"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = True

        result = component.merge_field_values()

        assert "full_name" in result[0].data
        assert "first_name" not in result[0].data
        assert "last_name" not in result[0].data
        # Other fields should remain
        assert "age" in result[0].data
        assert "salary" in result[0].data

    def test_multiple_merge_configs(self, component, sample_data):
        """Test multiple merge configurations"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            },
            {
                "new_field": "age_plus_salary",
                "operation": "A + B",
                "field_a": "age",
                "field_b": "salary",
                "separator": "",
                "value_type": "float",
            },
        ]
        component.drop_source_fields = False
        component.decimal_precision = 2

        result = component.merge_field_values()

        assert "full_name" in result[0].data
        assert "age_plus_salary" in result[0].data
        assert result[0].data["full_name"] == "John Doe"
        assert result[0].data["age_plus_salary"] == pytest.approx(5030.50, rel=1e-2)

    def test_field_not_found_error(self, component, sample_data):
        """Test error when field does not exist"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "result",
                "operation": "A LINK B",
                "field_a": "nonexistent_field",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = False

        with pytest.raises(ValueError) as excinfo:
            component.merge_field_values()

        assert "nonexistent_field" in str(excinfo.value)

    def test_missing_config_error(self, component):
        """Test error when config is missing"""
        component.data_input = []
        component.merge_configs = []

        with pytest.raises(ValueError):
            component.merge_field_values()

    def test_incomplete_config_skipped(self, component, sample_data):
        """Test that incomplete configs are skipped"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "",  # Empty new field
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            },
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            },
        ]
        component.drop_source_fields = False

        result = component.merge_field_values()

        # First config should be skipped, second should work
        assert "full_name" in result[0].data
        assert result[0].data["full_name"] == "John Doe"

    def test_extract_field_names(self, component, sample_data):
        """Test field name extraction"""
        fields = component._extract_field_names(sample_data)

        assert "first_name" in fields
        assert "last_name" in fields
        assert "age" in fields
        assert "salary" in fields
        assert len(fields) == 4

    def test_extract_field_names_empty(self, component):
        """Test field name extraction with empty data"""
        fields = component._extract_field_names([])

        assert fields == []

    def test_preview_fields(self, component, sample_data):
        """Test field preview functionality"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = False

        preview = component.preview_fields()

        assert "original_fields" in preview.data
        assert "new_fields" in preview.data
        assert "final_fields" in preview.data
        assert len(preview.data["new_fields"]) == 1
        assert preview.data["new_fields"][0]["field_name"] == "full_name"
        assert "full_name" in preview.data["final_fields"]

    def test_preview_fields_with_drop(self, component, sample_data):
        """Test field preview with drop source fields"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "full_name",
                "operation": "A LINK B",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": " ",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = True

        preview = component.preview_fields()

        assert "removed_fields" in preview.data
        assert "first_name" in preview.data["removed_fields"]
        assert "last_name" in preview.data["removed_fields"]
        assert "first_name" not in preview.data["final_fields"]
        assert "last_name" not in preview.data["final_fields"]
        assert "full_name" in preview.data["final_fields"]

    @pytest.mark.asyncio
    async def test_update_build_config_load_fields(self, component, sample_data):
        """Test update_build_config for loading fields"""
        # Mock get_upstream_data
        component.get_upstream_data = AsyncMock(return_value=sample_data)

        build_config = {
            "_graph_data": {"nodes": [], "edges": []},
            "_node_id": "test_node",
            "merge_configs": {
                "table_schema": [
                    {"name": "new_field"},
                    {"name": "operation"},
                    {"name": "field_a", "options": []},
                    {"name": "field_b", "options": []},
                    {"name": "separator"},
                    {"name": "value_type"},
                ]
            },
        }

        result = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="merge_configs", action="load_fields"
        )

        # Check that field options were populated
        assert len(result["merge_configs"]["table_schema"][2]["options"]) == 4  # field_a
        assert len(result["merge_configs"]["table_schema"][3]["options"]) == 4  # field_b
        assert "first_name" in result["merge_configs"]["table_schema"][2]["options"]
        assert "last_name" in result["merge_configs"]["table_schema"][3]["options"]

    def test_convert_value_type_string(self, component):
        """Test value type conversion to string"""
        series = pd.Series([1, 2, 3])
        result = component._convert_value_type(series, "string", 2)

        assert result.dtype == object
        assert result[0] == "1"

    def test_convert_value_type_integer(self, component):
        """Test value type conversion to integer"""
        series = pd.Series([1.7, 2.3, 3.9])
        result = component._convert_value_type(series, "integer", 2)

        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3

    def test_convert_value_type_float(self, component):
        """Test value type conversion to float with precision"""
        series = pd.Series([1.23456, 2.34567, 3.45678])
        result = component._convert_value_type(series, "float", 2)

        assert result[0] == pytest.approx(1.23, rel=1e-2)
        assert result[1] == pytest.approx(2.35, rel=1e-2)
        assert result[2] == pytest.approx(3.46, rel=1e-2)

    def test_convert_value_type_boolean(self, component):
        """Test value type conversion to boolean"""
        series = pd.Series([1, 0, 1])
        result = component._convert_value_type(series, "boolean", 2)

        assert result[0] is True
        assert result[1] is False
        assert result[2] is True

    def test_unknown_operation_fallback(self, component, sample_data):
        """Test unknown operation falls back to A LINK B"""
        component.data_input = sample_data
        component.merge_configs = [
            {
                "new_field": "result",
                "operation": "UNKNOWN_OP",
                "field_a": "first_name",
                "field_b": "last_name",
                "separator": "-",
                "value_type": "string",
            }
        ]
        component.drop_source_fields = False

        result = component.merge_field_values()

        # Should fall back to string concatenation
        assert result[0].data["result"] == "John-Doe"
