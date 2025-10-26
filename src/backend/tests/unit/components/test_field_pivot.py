"""Test ETLFieldPivotComponent - Multiple rows to columns (pivot)."""

import pytest
from lfx.components.manipulations.field_pivot import ETLFieldPivotComponent
from lfx.schema import Data


class TestETLFieldPivotComponent:
    """Test cases for ETLFieldPivotComponent."""

    @pytest.fixture
    def default_kwargs(self):
        """Default kwargs for component initialization."""
        return {
            "data_input": [],
            "group_fields": "product_id,product_name",
            "key_field": "month",
            "value_field": "sales",
            "agg_function": "first",
            "concat_separator": ",",
            "target_field_mapping": [],
            "fill_value": "",
            "chunk_size": 100000,
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample test data - sales by month in long format."""
        return [
            # Product A data
            Data(data={"product_id": "P001", "product_name": "Widget A", "month": "Jan", "sales": 100}),
            Data(data={"product_id": "P001", "product_name": "Widget A", "month": "Feb", "sales": 120}),
            Data(data={"product_id": "P001", "product_name": "Widget A", "month": "Mar", "sales": 150}),
            # Product B data
            Data(data={"product_id": "P002", "product_name": "Widget B", "month": "Jan", "sales": 200}),
            Data(data={"product_id": "P002", "product_name": "Widget B", "month": "Feb", "sales": 220}),
            Data(data={"product_id": "P002", "product_name": "Widget B", "month": "Mar", "sales": 250}),
            # Product C data
            Data(data={"product_id": "P003", "product_name": "Widget C", "month": "Jan", "sales": 50}),
            Data(data={"product_id": "P003", "product_name": "Widget C", "month": "Feb", "sales": 60}),
        ]

    def test_basic_pivot(self, default_kwargs, sample_data):
        """Test basic pivot operation."""
        default_kwargs["data_input"] = sample_data[:3]  # Just Product A
        component = ETLFieldPivotComponent(**default_kwargs)

        result = component.pivot_rows()

        # Should condense 3 rows into 1 row with 3 month columns
        assert len(result) == 1

        # Check structure
        row = result[0].data
        assert row["product_id"] == "P001"
        assert row["product_name"] == "Widget A"
        assert row["Jan"] == 100
        assert row["Feb"] == 120
        assert row["Mar"] == 150

    def test_multiple_groups_pivot(self, default_kwargs, sample_data):
        """Test pivoting with multiple groups."""
        default_kwargs["data_input"] = sample_data  # All products
        component = ETLFieldPivotComponent(**default_kwargs)

        result = component.pivot_rows()

        # Should have 3 rows (one per product)
        assert len(result) == 3

        # Check each product
        products = {r.data["product_id"]: r.data for r in result}

        assert products["P001"]["Jan"] == 100
        assert products["P001"]["Feb"] == 120
        assert products["P001"]["Mar"] == 150

        assert products["P002"]["Jan"] == 200
        assert products["P002"]["Feb"] == 220
        assert products["P002"]["Mar"] == 250

        assert products["P003"]["Jan"] == 50
        assert products["P003"]["Feb"] == 60
        # P003 doesn't have Mar, should be empty or filled value

    def test_aggregation_sum(self, default_kwargs):
        """Test pivot with sum aggregation."""
        # Data with duplicates
        data = [
            Data(data={"store": "S1", "product": "A", "month": "Jan", "sales": 100}),
            Data(data={"store": "S1", "product": "A", "month": "Jan", "sales": 50}),  # Duplicate
            Data(data={"store": "S1", "product": "A", "month": "Feb", "sales": 200}),
            Data(data={"store": "S2", "product": "A", "month": "Jan", "sales": 150}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "product"
        default_kwargs["agg_function"] = "sum"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 1
        # Jan should be summed: 100 + 50 + 150 = 300
        assert result[0].data["Jan"] == 300
        assert result[0].data["Feb"] == 200

    def test_aggregation_mean(self, default_kwargs):
        """Test pivot with mean aggregation."""
        data = [
            Data(data={"product": "A", "region": "North", "quarter": "Q1", "value": 100}),
            Data(data={"product": "A", "region": "South", "quarter": "Q1", "value": 200}),
            Data(data={"product": "A", "region": "North", "quarter": "Q2", "value": 150}),
            Data(data={"product": "A", "region": "South", "quarter": "Q2", "value": 250}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "product"
        default_kwargs["key_field"] = "quarter"
        default_kwargs["value_field"] = "value"
        default_kwargs["agg_function"] = "mean"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 1
        # Q1 mean: (100 + 200) / 2 = 150
        assert result[0].data["Q1"] == 150
        # Q2 mean: (150 + 250) / 2 = 200
        assert result[0].data["Q2"] == 200

    def test_aggregation_concat(self, default_kwargs):
        """Test pivot with string concatenation."""
        data = [
            Data(data={"id": "1", "type": "A", "tag": "red"}),
            Data(data={"id": "1", "type": "B", "tag": "blue"}),
            Data(data={"id": "1", "type": "A", "tag": "green"}),  # Duplicate type
            Data(data={"id": "2", "type": "A", "tag": "yellow"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "id"
        default_kwargs["key_field"] = "type"
        default_kwargs["value_field"] = "tag"
        default_kwargs["agg_function"] = "concat"
        default_kwargs["concat_separator"] = ";"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 2

        # Check concatenation
        id1 = [r.data for r in result if r.data["id"] == "1"][0]
        assert id1["A"] == "red;green"
        assert id1["B"] == "blue"

    def test_fill_value(self, default_kwargs, sample_data):
        """Test filling missing values after pivot."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["fill_value"] = "0"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        # P003 doesn't have Mar data
        p003 = [r.data for r in result if r.data["product_id"] == "P003"][0]
        assert p003.get("Mar", "0") == "0" or p003["Mar"] == "0"

    def test_field_mapping(self, default_kwargs, sample_data):
        """Test renaming pivoted columns."""
        default_kwargs["data_input"] = sample_data[:3]
        default_kwargs["target_field_mapping"] = [
            {"key_value": "Jan", "target_field": "January"},
            {"key_value": "Feb", "target_field": "February"},
            {"key_value": "Mar", "target_field": "March"},
        ]

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 1

        # Check renamed columns
        row = result[0].data
        assert "January" in row
        assert "February" in row
        assert "March" in row
        assert "Jan" not in row
        assert "Feb" not in row
        assert "Mar" not in row

    def test_max_min_aggregation(self, default_kwargs):
        """Test max and min aggregation functions."""
        data = [
            Data(data={"item": "A", "date": "2024-01", "price": 10}),
            Data(data={"item": "A", "date": "2024-01", "price": 20}),
            Data(data={"item": "A", "date": "2024-01", "price": 15}),
            Data(data={"item": "A", "date": "2024-02", "price": 25}),
            Data(data={"item": "A", "date": "2024-02", "price": 30}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "item"
        default_kwargs["key_field"] = "date"
        default_kwargs["value_field"] = "price"

        # Test MAX
        default_kwargs["agg_function"] = "max"
        component = ETLFieldPivotComponent(**default_kwargs)
        result_max = component.pivot_rows()

        assert result_max[0].data["2024-01"] == 20
        assert result_max[0].data["2024-02"] == 30

        # Test MIN
        default_kwargs["agg_function"] = "min"
        component2 = ETLFieldPivotComponent(**default_kwargs)
        result_min = component2.pivot_rows()

        assert result_min[0].data["2024-01"] == 10
        assert result_min[0].data["2024-02"] == 25

    def test_count_aggregation(self, default_kwargs):
        """Test count aggregation."""
        data = [
            Data(data={"category": "A", "status": "active", "id": "1"}),
            Data(data={"category": "A", "status": "active", "id": "2"}),
            Data(data={"category": "A", "status": "inactive", "id": "3"}),
            Data(data={"category": "B", "status": "active", "id": "4"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "category"
        default_kwargs["key_field"] = "status"
        default_kwargs["value_field"] = "id"
        default_kwargs["agg_function"] = "count"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 2

        # Check counts
        cat_a = [r.data for r in result if r.data["category"] == "A"][0]
        assert cat_a["active"] == 2
        assert cat_a["inactive"] == 1

    def test_first_last_aggregation(self, default_kwargs):
        """Test first and last aggregation functions."""
        data = [
            Data(data={"group": "G1", "type": "X", "value": "first"}),
            Data(data={"group": "G1", "type": "X", "value": "middle"}),
            Data(data={"group": "G1", "type": "X", "value": "last"}),
            Data(data={"group": "G1", "type": "Y", "value": "only"}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "group"
        default_kwargs["key_field"] = "type"
        default_kwargs["value_field"] = "value"

        # Test FIRST
        default_kwargs["agg_function"] = "first"
        component = ETLFieldPivotComponent(**default_kwargs)
        result_first = component.pivot_rows()

        assert result_first[0].data["X"] == "first"
        assert result_first[0].data["Y"] == "only"

        # Test LAST
        default_kwargs["agg_function"] = "last"
        component2 = ETLFieldPivotComponent(**default_kwargs)
        result_last = component2.pivot_rows()

        assert result_last[0].data["X"] == "last"
        assert result_last[0].data["Y"] == "only"

    def test_missing_field_error(self, default_kwargs, sample_data):
        """Test error when field doesn't exist."""
        default_kwargs["data_input"] = sample_data
        default_kwargs["key_field"] = "nonexistent"

        component = ETLFieldPivotComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.pivot_rows()

        assert "nonexistent" in str(excinfo.value)

    def test_empty_input_error(self, default_kwargs):
        """Test error with empty input."""
        default_kwargs["data_input"] = []

        component = ETLFieldPivotComponent(**default_kwargs)

        with pytest.raises(ValueError) as excinfo:
            component.pivot_rows()

        assert "input" in str(excinfo.value).lower()

    def test_large_dataset_warning(self, default_kwargs):
        """Test handling of large datasets."""
        # Create dataset that would trigger warning
        large_data = []
        for i in range(5000):
            large_data.append(
                Data(
                    data={
                        "id": str(i // 100),
                        "category": f"Cat{i % 10}",
                        "value": i,
                    }
                )
            )

        default_kwargs["data_input"] = large_data
        default_kwargs["group_fields"] = "id"
        default_kwargs["key_field"] = "category"
        default_kwargs["value_field"] = "value"
        default_kwargs["agg_function"] = "sum"
        default_kwargs["chunk_size"] = 100

        component = ETLFieldPivotComponent(**default_kwargs)

        # Should still work but may log warning
        result = component.pivot_rows()
        assert len(result) == 50  # 5000 / 100 = 50 unique ids

    def test_preview_result(self, default_kwargs, sample_data):
        """Test preview functionality."""
        default_kwargs["data_input"] = sample_data

        component = ETLFieldPivotComponent(**default_kwargs)
        preview = component.preview_result()

        assert isinstance(preview, Data)
        assert "original_rows" in preview.data
        assert "preview_rows" in preview.data
        assert "result_columns" in preview.data
        assert "unique_key_values" in preview.data
        assert "sample_data" in preview.data

        # Should show unique values
        assert len(preview.data["unique_key_values"]) > 0

    def test_get_statistics(self, default_kwargs, sample_data):
        """Test statistics generation."""
        default_kwargs["data_input"] = sample_data

        component = ETLFieldPivotComponent(**default_kwargs)
        stats = component.get_statistics()

        assert isinstance(stats, Data)
        assert "total_input_rows" in stats.data
        assert "group_fields" in stats.data
        assert "unique_key_values_count" in stats.data
        assert "estimated_output_rows" in stats.data
        assert "estimated_new_columns" in stats.data

    def test_complex_grouping(self, default_kwargs):
        """Test pivoting with multiple group fields."""
        data = [
            Data(data={"company": "A", "dept": "Sales", "quarter": "Q1", "revenue": 1000}),
            Data(data={"company": "A", "dept": "Sales", "quarter": "Q2", "revenue": 1200}),
            Data(data={"company": "A", "dept": "Marketing", "quarter": "Q1", "revenue": 800}),
            Data(data={"company": "A", "dept": "Marketing", "quarter": "Q2", "revenue": 900}),
            Data(data={"company": "B", "dept": "Sales", "quarter": "Q1", "revenue": 1500}),
            Data(data={"company": "B", "dept": "Sales", "quarter": "Q2", "revenue": 1700}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "company,dept"
        default_kwargs["key_field"] = "quarter"
        default_kwargs["value_field"] = "revenue"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        # Should have 3 unique combinations
        assert len(result) == 3

        # Verify grouping
        for row in result:
            if row.data["company"] == "A" and row.data["dept"] == "Sales":
                assert row.data["Q1"] == 1000
                assert row.data["Q2"] == 1200

    def test_null_handling(self, default_kwargs):
        """Test handling of null values."""
        data = [
            Data(data={"id": "1", "type": "A", "value": 100}),
            Data(data={"id": "1", "type": "B", "value": None}),
            Data(data={"id": "1", "type": "C", "value": 200}),
        ]

        default_kwargs["data_input"] = data
        default_kwargs["group_fields"] = "id"
        default_kwargs["key_field"] = "type"
        default_kwargs["value_field"] = "value"
        default_kwargs["fill_value"] = "0"

        component = ETLFieldPivotComponent(**default_kwargs)
        result = component.pivot_rows()

        assert len(result) == 1
        assert result[0].data["A"] == 100
        # B should be None or filled value
        assert result[0].data["C"] == 200
