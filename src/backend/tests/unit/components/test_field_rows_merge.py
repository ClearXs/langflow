"""Test ETLFieldRowsMergeComponent - Multiple rows merge into one."""

import pytest
from lfx.components.manipulations.field_rows_merge import ETLFieldRowsMergeComponent
from lfx.schema import Data


class TestETLFieldRowsMergeComponent:
    """Test cases for ETLFieldRowsMergeComponent."""

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component initialization."""
        return {
            "data_input": [],
            "merge_strategy": "merge_all",
            "group_by": "",
            "concat_separator": ";",
            "numeric_fields": "",
            "exclude_fields": "",
            "chunk_size": 100000,
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        return [
            Data(data={"id": "1", "name": "John", "age": 30, "city": "NYC", "tags": "developer"}),
            Data(data={"id": "2", "name": "Jane", "age": 25, "city": "LA", "tags": "designer"}),
            Data(data={"id": "3", "name": "Bob", "age": 35, "city": "Chicago", "tags": "manager"}),
            Data(data={"id": "4", "name": "Alice", "age": 28, "city": "NYC", "tags": "analyst"}),
        ]

    @pytest.fixture
    def grouped_data(self):
        """Create data suitable for grouped merging."""
        return [
            # Department A
            Data(data={"dept": "A", "employee": "John", "salary": 5000, "bonus": 500}),
            Data(data={"dept": "A", "employee": "Jane", "salary": 5500, "bonus": 600}),
            Data(data={"dept": "A", "employee": "Bob", "salary": 6000, "bonus": 700}),
            # Department B
            Data(data={"dept": "B", "employee": "Alice", "salary": 5200, "bonus": 550}),
            Data(data={"dept": "B", "employee": "Charlie", "salary": 5800, "bonus": 650}),
        ]

    def test_keep_first_strategy(self, default_kwargs, sample_data):
        """Test keep_first merge strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "keep_first"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should keep only the first row
        assert len(result) == 1
        assert result[0].data["id"] == "1"
        assert result[0].data["name"] == "John"

    def test_keep_last_strategy(self, default_kwargs, sample_data):
        """Test keep_last merge strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "keep_last"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should keep only the last row
        assert len(result) == 1
        assert result[0].data["id"] == "4"
        assert result[0].data["name"] == "Alice"

    def test_merge_all_strategy(self, default_kwargs, sample_data):
        """Test merge_all strategy - concatenates all values."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "merge_all"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should merge all rows into one
        assert len(result) == 1

        # Check concatenated values
        row = result[0].data
        assert "John" in row["name"]
        assert "Jane" in row["name"]
        assert "Bob" in row["name"]
        assert "Alice" in row["name"]

        # Check separator is used
        assert default_kwargs["concat_separator"] in row["name"]

    def test_sum_strategy(self, default_kwargs, sample_data):
        """Test sum aggregation strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["numeric_fields"] = "age"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Sum of ages: 30 + 25 + 35 + 28 = 118
        assert result[0].data["age"] == 118

    def test_mean_strategy(self, default_kwargs, sample_data):
        """Test mean aggregation strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "mean"
        default_kwargs["numeric_fields"] = "age"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Mean of ages: (30 + 25 + 35 + 28) / 4 = 29.5
        assert result[0].data["age"] == 29.5

    def test_max_strategy(self, default_kwargs, sample_data):
        """Test max aggregation strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "max"
        default_kwargs["numeric_fields"] = "age"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Max age: 35
        assert result[0].data["age"] == 35

    def test_min_strategy(self, default_kwargs, sample_data):
        """Test min aggregation strategy."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "min"
        default_kwargs["numeric_fields"] = "age"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Min age: 25
        assert result[0].data["age"] == 25

    def test_concat_strategy(self, default_kwargs, sample_data):
        """Test concat strategy with custom separator."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "concat"
        default_kwargs["concat_separator"] = " | "

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1

        # Check custom separator is used
        row = result[0].data
        assert " | " in row["name"]
        assert row["name"] == "John | Jane | Bob | Alice"

    def test_group_by_merging(self, default_kwargs, grouped_data):
        """Test merging with group_by fields."""
        default_kwargs["data_input"] = grouped_data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["group_by"] = "dept"
        default_kwargs["numeric_fields"] = "salary,bonus"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should have 2 rows (one per department)
        assert len(result) == 2

        # Check department totals
        dept_data = {r.data["dept"]: r.data for r in result}

        # Dept A: 5000 + 5500 + 6000 = 16500
        assert dept_data["A"]["salary"] == 16500
        # Dept A bonus: 500 + 600 + 700 = 1800
        assert dept_data["A"]["bonus"] == 1800

        # Dept B: 5200 + 5800 = 11000
        assert dept_data["B"]["salary"] == 11000
        # Dept B bonus: 550 + 650 = 1200
        assert dept_data["B"]["bonus"] == 1200

    def test_exclude_fields(self, default_kwargs, sample_data):
        """Test excluding fields from merging."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "merge_all"
        default_kwargs["exclude_fields"] = "id,age"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1

        row = result[0].data
        # Excluded fields should keep first value
        assert row["id"] == "1"
        assert row["age"] == 30

        # Other fields should be merged
        assert "John" in row["name"]
        assert "Jane" in row["name"]

    def test_auto_detect_numeric_fields(self, default_kwargs, sample_data):
        """Test automatic detection of numeric fields."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["numeric_fields"] = ""  # Empty, should auto-detect

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Should auto-detect and sum age field
        assert result[0].data["age"] == 118

    def test_handle_null_values(self, default_kwargs):
        """Test handling null values during merge."""
        data = [
            Data(data={"id": "1", "value": 100, "text": "A"}),
            Data(data={"id": "2", "value": None, "text": "B"}),
            Data(data={"id": "3", "value": 200, "text": None}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["numeric_fields"] = "value"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Should handle None values: 100 + 200 = 300
        assert result[0].data["value"] == 300

    def test_empty_values_in_concat(self, default_kwargs):
        """Test concatenation with empty values."""
        data = [
            Data(data={"id": "1", "text": "Hello"}),
            Data(data={"id": "2", "text": ""}),
            Data(data={"id": "3", "text": "World"}),
            Data(data={"id": "4", "text": None}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["merge_strategy"] = "concat"
        default_kwargs["concat_separator"] = " "

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1
        # Should skip empty and None values
        assert result[0].data["text"] == "Hello World"

    def test_multiple_group_fields(self, default_kwargs):
        """Test grouping by multiple fields."""
        data = [
            Data(data={"company": "A", "dept": "Sales", "year": 2023, "revenue": 1000}),
            Data(data={"company": "A", "dept": "Sales", "year": 2023, "revenue": 1500}),
            Data(data={"company": "A", "dept": "Sales", "year": 2024, "revenue": 2000}),
            Data(data={"company": "A", "dept": "Marketing", "year": 2023, "revenue": 800}),
            Data(data={"company": "B", "dept": "Sales", "year": 2023, "revenue": 1200}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["group_by"] = "company,dept,year"
        default_kwargs["numeric_fields"] = "revenue"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should have 4 unique combinations
        assert len(result) == 4

        # Check specific group
        for row in result:
            if row.data["company"] == "A" and row.data["dept"] == "Sales" and row.data["year"] == 2023:
                assert row.data["revenue"] == 2500  # 1000 + 1500

    def test_missing_field_error(self, default_kwargs, sample_data):
        """Test error when group field doesn't exist."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["group_by"] = "nonexistent_field"

        component = ETLFieldRowsMergeComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.merge_rows()

        assert "nonexistent_field" in str(excinfo.value)

    def test_empty_input_error(self, default_kwargs):
        """Test error with empty input."""
        default_kwargs["data_input"] = []

        component = ETLFieldRowsMergeComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.merge_rows()

        assert "input" in str(excinfo.value).lower()

    def test_large_dataset_chunking(self, default_kwargs):
        """Test chunking for large datasets with grouping."""
        # Create large dataset
        large_data = []
        for i in range(1000):
            large_data.append(
                Data(
                    data={
                        "group": f"G{i % 10}",  # 10 groups
                        "value": i,
                        "text": f"Item{i}",
                    }
                )
            )

        default_kwargs["data_input"] = large_data
        default_kwargs["merge_strategy"] = "sum"
        default_kwargs["group_by"] = "group"
        default_kwargs["numeric_fields"] = "value"
        default_kwargs["chunk_size"] = 100  # Small chunk for testing

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should have 10 groups
        assert len(result) == 10

        # Verify sum for group G0: 0 + 10 + 20 + ... + 990 = sum of arithmetic sequence
        g0_row = [r for r in result if r.data["group"] == "G0"][0]
        expected_sum = sum(range(0, 1000, 10))
        assert g0_row.data["value"] == expected_sum

    def test_preview_result(self, default_kwargs, sample_data):
        """Test preview functionality."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["merge_strategy"] = "concat"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        preview = component.preview_result()

        assert isinstance(preview, Data)
        assert "original_rows" in preview.data
        assert "preview_rows" in preview.data
        assert "merge_strategy" in preview.data
        assert "sample_data" in preview.data

    def test_get_statistics(self, default_kwargs, grouped_data):
        """Test statistics generation."""
        default_kwargs["data_input"] = grouped_data
        default_kwargs["group_by"] = "dept"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        stats = component.get_statistics()

        assert isinstance(stats, Data)
        assert "total_input_rows" in stats.data
        assert "unique_groups" in stats.data
        assert "avg_rows_per_group" in stats.data
        assert "estimated_output_rows" in stats.data

        # Check statistics
        assert stats.data["total_input_rows"] == 5
        assert stats.data["unique_groups"] == 2
        assert stats.data["estimated_output_rows"] == 2

    def test_mixed_data_types(self, default_kwargs):
        """Test merging with mixed data types."""
        data = [
            Data(data={"id": 1, "value": 10.5, "flag": True, "text": "A"}),
            Data(data={"id": 2, "value": 20.3, "flag": False, "text": "B"}),
            Data(data={"id": 3, "value": 15.2, "flag": True, "text": "C"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["merge_strategy"] = "merge_all"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 1

        row = result[0].data
        # Check different data types are handled
        assert "1" in str(row["id"]) or row["id"] == 1
        assert row["text"] == "A;B;C"

    def test_count_aggregation(self, default_kwargs, grouped_data):
        """Test implicit count aggregation."""
        default_kwargs["data_input"] = grouped_data
        default_kwargs["merge_strategy"] = "merge_all"
        default_kwargs["group_by"] = "dept"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        assert len(result) == 2

        # Check employee names are concatenated per department
        dept_data = {r.data["dept"]: r.data for r in result}
        assert "John" in dept_data["A"]["employee"]
        assert "Jane" in dept_data["A"]["employee"]
        assert "Bob" in dept_data["A"]["employee"]

    def test_single_row_input(self, default_kwargs):
        """Test merging with single row input."""
        data = [
            Data(data={"id": "1", "value": 100}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["merge_strategy"] = "sum"

        component = ETLFieldRowsMergeComponent(**default_kwargs)
        result = component.merge_rows()

        # Should return the same single row
        assert len(result) == 1
        assert result[0].data["id"] == "1"
        assert result[0].data["value"] == 100

    def test_custom_separator_variations(self, default_kwargs):
        """Test different custom separators."""
        data = [
            Data(data={"items": "A"}),
            Data(data={"items": "B"}),
            Data(data={"items": "C"}),
        ]

        separators = [" | ", ", ", " - ", "\n", "\t"]

        for sep in separators:
            default_kwargs["data_input"] = data
            default_kwargs["merge_strategy"] = "concat"
            default_kwargs["concat_separator"] = sep

            component = ETLFieldRowsMergeComponent(**default_kwargs)
            result = component.merge_rows()

            assert len(result) == 1
            assert result[0].data["items"] == f"A{sep}B{sep}C"
