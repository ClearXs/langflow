"""Test ETLFieldSplitComponent - Single column to multiple rows."""

import pytest
from lfx.components.manipulations.field_split import ETLFieldSplitComponent
from lfx.schema import Data


class TestETLFieldSplitComponent:
    """Test cases for ETLFieldSplitComponent."""

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component initialization."""
        return {
            "data_input": [],
            "split_field": "tags",
            "separator": ",",
            "separator_type": "fixed_string",
            "custom_rule_id": "",
            "reset_index": False,
            "keep_empty": False,
            "chunk_size": 100000,
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        return [
            Data(data={"id": "1", "name": "Product A", "tags": "electronics,mobile,smartphone"}),
            Data(data={"id": "2", "name": "Product B", "tags": "clothing,casual,summer"}),
            Data(data={"id": "3", "name": "Product C", "tags": "home,kitchen"}),
            Data(data={"id": "4", "name": "Product D", "tags": ""}),  # Empty field
            Data(data={"id": "5", "name": "Product E", "tags": None}),  # Null field
        ]

    def test_basic_split(self, default_kwargs, sample_data):
        """Test basic field splitting with comma separator."""
        default_kwargs["data_input"] = sample_data[:3]
        component = ETLFieldSplitComponent(**default_kwargs)

        result = component.split_rows()

        # Should expand 3 rows to 8 rows (3+3+2)
        assert len(result) == 8

        # Check first product expanded correctly
        product_a_rows = [r.data for r in result if r.data["id"] == "1"]
        assert len(product_a_rows) == 3
        assert product_a_rows[0]["tags"] == "electronics"
        assert product_a_rows[1]["tags"] == "mobile"
        assert product_a_rows[2]["tags"] == "smartphone"

    def test_regex_separator(self, default_kwargs, sample_data):
        """Test splitting with regex separator."""
        # Create data with mixed separators
        data = [
            Data(data={"id": "1", "text": "apple;orange,banana|grape"}),
            Data(data={"id": "2", "text": "car;bike|train"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "text"
        default_kwargs["separator"] = "[;,|]"
        default_kwargs["separator_type"] = "regex"

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should expand to 7 rows (4+3)
        assert len(result) == 7

        # Check all values are split correctly
        values = [r.data["text"] for r in result]
        assert "apple" in values
        assert "orange" in values
        assert "banana" in values
        assert "grape" in values
        assert "car" in values
        assert "bike" in values
        assert "train" in values

    def test_line_separator(self, default_kwargs):
        """Test splitting with line separator special keyword."""
        data = [
            Data(data={"id": "1", "lines": "line1\nline2\nline3"}),
            Data(data={"id": "2", "lines": "single"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "lines"
        default_kwargs["separator"] = "line.separator"
        default_kwargs["separator_type"] = "fixed_string"

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should expand to 4 rows (3+1)
        assert len(result) == 4

        # Check lines are split correctly
        lines = [r.data["lines"] for r in result if r.data["id"] == "1"]
        assert lines == ["line1", "line2", "line3"]

    def test_reset_index(self, default_kwargs, sample_data):
        """Test index reset functionality."""
        default_kwargs["data_input"] = sample_data[:2]
        default_kwargs["reset_index"] = True

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should have sequential index
        assert len(result) == 6  # 3+3
        # Data objects don't have index, but the internal DataFrame should

    def test_keep_empty_values(self, default_kwargs):
        """Test keeping empty values after split."""
        data = [
            Data(data={"id": "1", "items": "a,,b,c,"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "items"
        default_kwargs["keep_empty"] = True

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should keep empty strings
        assert len(result) == 5
        values = [r.data["items"] for r in result]
        assert "" in values

    def test_dont_keep_empty_values(self, default_kwargs):
        """Test filtering empty values after split."""
        data = [
            Data(data={"id": "1", "items": "a,,b,c,"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "items"
        default_kwargs["keep_empty"] = False

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should filter empty strings
        assert len(result) == 3
        values = [r.data["items"] for r in result]
        assert "" not in values
        assert values == ["a", "b", "c"]

    def test_handle_null_values(self, default_kwargs, sample_data):
        """Test handling of null and empty values."""
        default_kwargs["data_input"] = sample_data[3:5]  # Empty and None
        default_kwargs["keep_empty"] = False

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Empty and None values should be handled gracefully
        assert len(result) == 0  # Both rows have no valid split values

    def test_missing_field(self, default_kwargs, sample_data):
        """Test error handling for missing field."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["split_field"] = "nonexistent_field"

        component = ETLFieldSplitComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.split_rows()

        assert "nonexistent_field" in str(excinfo.value)

    def test_empty_input(self, default_kwargs):
        """Test handling of empty input."""
        default_kwargs["data_input"] = []

        component = ETLFieldSplitComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.split_rows()

        # Should raise error about no input data
        assert "input" in str(excinfo.value).lower()

    def test_large_dataset_chunking(self, default_kwargs):
        """Test chunking for large datasets."""
        # Create large dataset
        large_data = []
        for i in range(1000):
            large_data.append(
                Data(
                    data={
                        "id": str(i),
                        "tags": "tag1,tag2,tag3",
                    }
                )
            )

        default_kwargs["data_input"] = large_data
        default_kwargs["chunk_size"] = 100  # Small chunk for testing

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        # Should expand 1000 rows to 3000 rows
        assert len(result) == 3000

        # Verify data integrity
        assert all(r.data["tags"] in ["tag1", "tag2", "tag3"] for r in result)

    def test_preview_result(self, default_kwargs, sample_data):
        """Test preview functionality."""
        default_kwargs["data_input"] = sample_data[:3]

        component = ETLFieldSplitComponent(**default_kwargs)
        preview = component.preview_result()

        assert isinstance(preview, Data)
        assert "original_rows" in preview.data
        assert "preview_rows" in preview.data
        assert "split_field" in preview.data
        assert "separator" in preview.data
        assert "sample_data" in preview.data

        # Preview should show limited rows
        assert len(preview.data["sample_data"]) <= 20

    def test_get_statistics(self, default_kwargs, sample_data):
        """Test statistics generation."""
        default_kwargs["data_input"] = sample_data[:3]

        component = ETLFieldSplitComponent(**default_kwargs)
        stats = component.get_statistics()

        assert isinstance(stats, Data)
        assert "total_input_rows" in stats.data
        assert "total_columns" in stats.data
        assert "split_field" in stats.data
        assert "separator_type" in stats.data

        # Check statistics accuracy
        assert stats.data["total_input_rows"] == 3
        assert stats.data["split_field"] == "tags"

    def test_custom_rule_placeholder(self, default_kwargs, sample_data):
        """Test custom rule ID (placeholder for future implementation)."""
        default_kwargs["data_input"] = sample_data[:1]
        default_kwargs["separator_type"] = "custom_rule"
        default_kwargs["custom_rule_id"] = "rule_123"

        component = ETLFieldSplitComponent(**default_kwargs)

        # Currently should fall back to comma
        result = component.split_rows()
        assert len(result) == 3  # Split by comma as fallback

    def test_special_characters_in_data(self, default_kwargs):
        """Test handling special characters in data."""
        data = [
            Data(
                data={
                    "id": "1",
                    "text": "hello|world|test@example.com|data#2024",
                }
            )
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "text"
        default_kwargs["separator"] = "|"

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        assert len(result) == 4
        values = [r.data["text"] for r in result]
        assert "test@example.com" in values
        assert "data#2024" in values

    def test_preserve_other_fields(self, default_kwargs):
        """Test that other fields are preserved during split."""
        data = [
            Data(
                data={
                    "id": "1",
                    "name": "Test",
                    "category": "A",
                    "tags": "x,y,z",
                    "value": 100,
                }
            )
        ]

        default_kwargs["data_input"] = data
        default_kwargs["split_field"] = "tags"

        component = ETLFieldSplitComponent(**default_kwargs)
        result = component.split_rows()

        assert len(result) == 3

        # All other fields should be preserved
        for row in result:
            assert row.data["id"] == "1"
            assert row.data["name"] == "Test"
            assert row.data["category"] == "A"
            assert row.data["value"] == 100
            assert row.data["tags"] in ["x", "y", "z"]

    async def test_update_build_config(self, default_kwargs, sample_data):
        """Test dynamic field loading."""
        default_kwargs["data_input"] = sample_data[:1]

        component = ETLFieldSplitComponent(**default_kwargs)

        # Mock build_config
        build_config = {
            "split_field": {
                "options": [],
            }
        }

        updated_config = await component.update_build_config(
            build_config=build_config, field_value="data_input", field_name="split_field"
        )

        # Should populate field options
        assert len(updated_config["split_field"]["options"]) > 0
        assert "id" in updated_config["split_field"]["options"]
        assert "name" in updated_config["split_field"]["options"]
        assert "tags" in updated_config["split_field"]["options"]
