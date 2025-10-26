"""Test ETLFieldSplitToColumnsComponent - Single column to multiple columns."""

import pytest
from lfx.components.manipulations.field_split_to_columns import ETLFieldSplitToColumnsComponent
from lfx.schema import Data


class TestETLFieldSplitToColumnsComponent:
    """Test cases for ETLFieldSplitToColumnsComponent."""

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component initialization."""
        return {
            "data_input": [],
            "split_field": "full_name",
            "separator": " ",
            "separator_type": "fixed_string",
            "custom_rule_id": "",
            "new_fields_config": [
                {"field_name": "first_name", "field_order": 1},
                {"field_name": "last_name", "field_order": 2},
            ],
            "keep_original": False,
            "fill_missing": "",
            "chunk_size": 100000,
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        return [
            Data(data={"id": "1", "full_name": "John Doe", "age": 30}),
            Data(data={"id": "2", "full_name": "Jane Smith Johnson", "age": 25}),
            Data(data={"id": "3", "full_name": "Bob", "age": 35}),
            Data(data={"id": "4", "full_name": "", "age": 40}),
            Data(data={"id": "5", "full_name": None, "age": 45}),
        ]

    def test_basic_column_split(self, default_kwargs, sample_data):
        """Test basic field splitting into columns."""
        default_kwargs["data_input"] = sample_data[:2]
        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        result = component.split_to_columns()

        # Should still have 2 rows
        assert len(result) == 2

        # Check first row
        assert result[0].data["first_name"] == "John"
        assert result[0].data["last_name"] == "Doe"
        assert result[0].data["age"] == 30

        # Check second row (3 parts, only takes first 2)
        assert result[1].data["first_name"] == "Jane"
        assert result[1].data["last_name"] == "Smith"

    def test_keep_original_field(self, default_kwargs, sample_data):
        """Test keeping the original field after split."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["keep_original"] = True

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        assert "full_name" in result[0].data
        assert result[0].data["full_name"] == "John Doe"
        assert result[0].data["first_name"] == "John"
        assert result[0].data["last_name"] == "Doe"

    def test_remove_original_field(self, default_kwargs, sample_data):
        """Test removing the original field after split."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["keep_original"] = False

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        assert "full_name" not in result[0].data
        assert result[0].data["first_name"] == "John"
        assert result[0].data["last_name"] == "Doe"

    def test_fill_missing_values(self, default_kwargs, sample_data):
        """Test filling missing values when split parts are fewer than expected."""
        default_kwargs["data_input"] = sample_data[2:3]  # "Bob" only
        default_kwargs["fill_missing"] = "N/A"

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        assert result[0].data["first_name"] == "Bob"
        assert result[0].data["last_name"] == "N/A"

    def test_complex_separator(self, default_kwargs):
        """Test with complex separators."""
        data = [
            Data(data={"id": "1", "info": "name:John|age:30|city:NYC"}),
            Data(data={"id": "2", "info": "name:Jane|age:25|city:LA"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "info"
        default_kwargs["separator"] = "|"
        default_kwargs["new_fields_config"] = [
            {"field_name": "name_field", "field_order": 1},
            {"field_name": "age_field", "field_order": 2},
            {"field_name": "city_field", "field_order": 3},
        ]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 2
        assert result[0].data["name_field"] == "name:John"
        assert result[0].data["age_field"] == "age:30"
        assert result[0].data["city_field"] == "city:NYC"

    def test_regex_separator(self, default_kwargs):
        """Test splitting with regex separator."""
        data = [
            Data(data={"id": "1", "mixed": "a_1-b_2-c_3"}),
            Data(data={"id": "2", "mixed": "x_4-y_5-z_6"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "mixed"
        default_kwargs["separator"] = "[-_]"
        default_kwargs["separator_type"] = "regex"
        default_kwargs["new_fields_config"] = [
            {"field_name": "part1", "field_order": 1},
            {"field_name": "part2", "field_order": 2},
            {"field_name": "part3", "field_order": 3},
            {"field_name": "part4", "field_order": 4},
            {"field_name": "part5", "field_order": 5},
            {"field_name": "part6", "field_order": 6},
        ]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 2
        # First row: a, 1, b, 2, c, 3
        assert result[0].data["part1"] == "a"
        assert result[0].data["part2"] == "1"
        assert result[0].data["part3"] == "b"
        assert result[0].data["part4"] == "2"
        assert result[0].data["part5"] == "c"
        assert result[0].data["part6"] == "3"

    def test_handle_empty_and_null(self, default_kwargs, sample_data):
        """Test handling empty and null values."""
        default_kwargs["data_input"] = sample_data[3:5]  # Empty and None
        default_kwargs["fill_missing"] = "EMPTY"

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 2

        # Empty string row
        assert result[0].data["first_name"] == "EMPTY"
        assert result[0].data["last_name"] == "EMPTY"

        # None row
        assert result[1].data["first_name"] == "EMPTY"
        assert result[1].data["last_name"] == "EMPTY"

    def test_field_order_configuration(self, default_kwargs):
        """Test that field ordering configuration works correctly."""
        data = [
            Data(data={"id": "1", "parts": "A-B-C-D"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "parts"
        default_kwargs["separator"] = "-"
        default_kwargs["new_fields_config"] = [
            {"field_name": "fourth", "field_order": 4},
            {"field_name": "second", "field_order": 2},
            {"field_name": "first", "field_order": 1},
            {"field_name": "third", "field_order": 3},
        ]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        assert result[0].data["first"] == "A"
        assert result[0].data["second"] == "B"
        assert result[0].data["third"] == "C"
        assert result[0].data["fourth"] == "D"

    def test_missing_field_error(self, default_kwargs, sample_data):
        """Test error when split field doesn't exist."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["split_field"] = "nonexistent"

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.split_to_columns()

        assert "nonexistent" in str(excinfo.value)

    def test_empty_input_error(self, default_kwargs):
        """Test error with empty input."""
        default_kwargs["data_input"] = []

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.split_to_columns()

        assert "input" in str(excinfo.value).lower()

    def test_no_fields_config_error(self, default_kwargs, sample_data):
        """Test error when no field configuration is provided."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["new_fields_config"] = []

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.split_to_columns()

        assert "field" in str(excinfo.value).lower()

    def test_large_dataset_chunking(self, default_kwargs):
        """Test chunking for large datasets."""
        # Create large dataset
        large_data = []
        for i in range(1000):
            large_data.append(
                Data(
                    data={
                        "id": str(i),
                        "name": f"First{i} Last{i}",
                    }
                )
            )

        default_kwargs["data_input"] = large_data
        default_kwargs["split_field"] = "name"
        default_kwargs["chunk_size"] = 100  # Small chunk for testing

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1000

        # Verify data integrity
        assert result[0].data["first_name"] == "First0"
        assert result[0].data["last_name"] == "Last0"
        assert result[999].data["first_name"] == "First999"
        assert result[999].data["last_name"] == "Last999"

    def test_preview_result(self, default_kwargs, sample_data):
        """Test preview functionality."""
        default_kwargs["data_input"] = sample_data[:3]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        preview = component.preview_result()

        assert isinstance(preview, Data)
        assert "original_rows" in preview.data
        assert "split_field" in preview.data
        assert "new_columns" in preview.data
        assert "sample_data" in preview.data

        # Preview should show limited rows
        assert len(preview.data["sample_data"]) <= 20

    def test_get_statistics(self, default_kwargs, sample_data):
        """Test statistics generation."""
        default_kwargs["data_input"] = sample_data[:3]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        stats = component.get_statistics()

        assert isinstance(stats, Data)
        assert "total_input_rows" in stats.data
        assert "original_columns" in stats.data
        assert "new_columns_count" in stats.data
        assert "split_field" in stats.data

        assert stats.data["total_input_rows"] == 3
        assert stats.data["new_columns_count"] == 2

    def test_custom_rule_placeholder(self, default_kwargs, sample_data):
        """Test custom rule ID (placeholder)."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["separator_type"] = "custom_rule"
        default_kwargs["custom_rule_id"] = "rule_456"

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        # Should fall back to space
        result = component.split_to_columns()
        assert len(result) == 1
        assert result[0].data["first_name"] == "John"
        assert result[0].data["last_name"] == "Doe"

    def test_preserve_other_fields(self, default_kwargs, sample_data):
        """Test that other fields are preserved."""
        default_kwargs["data_input"] = sample_data[:1]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        # Original fields preserved
        assert result[0].data["id"] == "1"
        assert result[0].data["age"] == 30
        # New fields added
        assert result[0].data["first_name"] == "John"
        assert result[0].data["last_name"] == "Doe"

    def test_tab_separator(self, default_kwargs):
        """Test with tab separator."""
        data = [
            Data(data={"id": "1", "tsv": "col1\tcol2\tcol3"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "tsv"
        default_kwargs["separator"] = "\t"
        default_kwargs["new_fields_config"] = [
            {"field_name": "field1", "field_order": 1},
            {"field_name": "field2", "field_order": 2},
            {"field_name": "field3", "field_order": 3},
        ]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)
        result = component.split_to_columns()

        assert len(result) == 1
        assert result[0].data["field1"] == "col1"
        assert result[0].data["field2"] == "col2"
        assert result[0].data["field3"] == "col3"

    async def test_update_build_config(self, default_kwargs, sample_data):
        """Test dynamic field loading and table population."""
        default_kwargs["data_input"] = sample_data[:1]

        component = ETLFieldSplitToColumnsComponent(**default_kwargs)

        # Mock build_config
        build_config = {
            "split_field": {
                "options": [],
            },
            "new_fields_config": {
                "value": [],
            },
        }

        # Test field loading
        updated_config = await component.update_build_config(
            build_config=build_config, field_value="data_input", field_name="split_field"
        )

        assert len(updated_config["split_field"]["options"]) > 0
        assert "full_name" in updated_config["split_field"]["options"]

        # Test auto-populate table
        default_kwargs["split_field"] = "full_name"
        default_kwargs["separator"] = " "
        component2 = ETLFieldSplitToColumnsComponent(**default_kwargs)

        updated_config2 = await component2.update_build_config(
            build_config=build_config, field_value=" ", field_name="separator"
        )

        # Should auto-populate table with field suggestions
        assert len(updated_config2["new_fields_config"]["value"]) == 2
        assert updated_config2["new_fields_config"]["value"][0]["field_name"] == "field_1"
        assert updated_config2["new_fields_config"]["value"][1]["field_name"] == "field_2"
