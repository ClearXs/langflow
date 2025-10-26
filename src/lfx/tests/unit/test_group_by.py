"""Unit tests for ETLGroupByComponent."""

import pytest

from lfx.components.operations.group_by import ETLGroupByComponent
from lfx.schema import Data


class TestETLGroupByComponent:
    """Test suite for Group By component."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return [
            Data(data={"product_id": "A", "category": "Electronics", "quantity": 10, "price": 100.0}),
            Data(data={"product_id": "B", "category": "Electronics", "quantity": 5, "price": 200.0}),
            Data(data={"product_id": "C", "category": "Clothing", "quantity": 20, "price": 50.0}),
            Data(data={"product_id": "D", "category": "Clothing", "quantity": 15, "price": 75.0}),
            Data(data={"product_id": "E", "category": "Electronics", "quantity": 8, "price": 150.0}),
        ]

    def test_basic_groupby_with_sum(self, sample_data):
        """Test basic group by with sum aggregation."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "quantity", "agg_function": "sum", "alias": "total_quantity"}],
        )

        result = component.group_data()

        # Should have 2 groups: Electronics and Clothing
        assert len(result) == 2

        # Convert to dict for easier checking
        result_dict = {item.data["category"]: item.data for item in result}

        # Electronics: 10 + 5 + 8 = 23
        assert result_dict["Electronics"]["total_quantity"] == 23

        # Clothing: 20 + 15 = 35
        assert result_dict["Clothing"]["total_quantity"] == 35

    def test_groupby_with_count(self, sample_data):
        """Test group by with count aggregation."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "product_id", "agg_function": "count", "alias": "product_count"}],
        )

        result = component.group_data()

        result_dict = {item.data["category"]: item.data for item in result}

        # Electronics: 3 products (A, B, E)
        assert result_dict["Electronics"]["product_count"] == 3

        # Clothing: 2 products (C, D)
        assert result_dict["Clothing"]["product_count"] == 2

    def test_groupby_with_avg(self, sample_data):
        """Test group by with average aggregation."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "price", "agg_function": "avg", "alias": "avg_price"}],
        )

        result = component.group_data()

        result_dict = {item.data["category"]: item.data for item in result}

        # Electronics: (100 + 200 + 150) / 3 = 150
        assert result_dict["Electronics"]["avg_price"] == pytest.approx(150.0)

        # Clothing: (50 + 75) / 2 = 62.5
        assert result_dict["Clothing"]["avg_price"] == pytest.approx(62.5)

    def test_groupby_with_min_max(self, sample_data):
        """Test group by with min and max aggregations."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "price", "agg_function": "min", "alias": "min_price"},
                {"field_name": "price", "agg_function": "max", "alias": "max_price"},
            ],
        )

        result = component.group_data()

        result_dict = {item.data["category"]: item.data for item in result}

        # Electronics
        assert result_dict["Electronics"]["min_price"] == 100.0
        assert result_dict["Electronics"]["max_price"] == 200.0

        # Clothing
        assert result_dict["Clothing"]["min_price"] == 50.0
        assert result_dict["Clothing"]["max_price"] == 75.0

    def test_groupby_with_count_distinct(self):
        """Test group by with count distinct aggregation."""
        data = [
            Data(data={"store": "A", "product": "Laptop", "sale_id": 1}),
            Data(data={"store": "A", "product": "Laptop", "sale_id": 2}),
            Data(data={"store": "A", "product": "Phone", "sale_id": 3}),
            Data(data={"store": "B", "product": "Laptop", "sale_id": 4}),
            Data(data={"store": "B", "product": "Laptop", "sale_id": 5}),
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "store"}],
            aggregations=[{"field_name": "product", "agg_function": "count_distinct", "alias": "unique_products"}],
        )

        result = component.group_data()

        result_dict = {item.data["store"]: item.data for item in result}

        # Store A has 2 unique products (Laptop, Phone)
        assert result_dict["A"]["unique_products"] == 2

        # Store B has 1 unique product (Laptop)
        assert result_dict["B"]["unique_products"] == 1

    def test_multiple_group_by_columns(self, sample_data):
        """Test group by with multiple grouping columns."""
        data = [
            Data(data={"year": 2024, "quarter": "Q1", "sales": 100}),
            Data(data={"year": 2024, "quarter": "Q1", "sales": 150}),
            Data(data={"year": 2024, "quarter": "Q2", "sales": 200}),
            Data(data={"year": 2023, "quarter": "Q1", "sales": 80}),
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "year"}, {"selected": True, "field_name": "quarter"}],
            aggregations=[{"field_name": "sales", "agg_function": "sum", "alias": "total_sales"}],
        )

        result = component.group_data()

        # Should have 3 groups: (2024, Q1), (2024, Q2), (2023, Q1)
        assert len(result) == 3

        # Find (2024, Q1) group
        q1_2024 = next(item for item in result if item.data["year"] == 2024 and item.data["quarter"] == "Q1")
        assert q1_2024.data["total_sales"] == 250  # 100 + 150

    def test_multiple_aggregations_same_field(self, sample_data):
        """Test multiple aggregations on the same field."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "price", "agg_function": "sum", "alias": "total_price"},
                {"field_name": "price", "agg_function": "avg", "alias": "avg_price"},
                {"field_name": "price", "agg_function": "count", "alias": "count_price"},
            ],
        )

        result = component.group_data()

        result_dict = {item.data["category"]: item.data for item in result}

        electronics = result_dict["Electronics"]
        assert electronics["total_price"] == 450.0  # 100 + 200 + 150
        assert electronics["avg_price"] == pytest.approx(150.0)
        assert electronics["count_price"] == 3

    def test_sort_results(self, sample_data):
        """Test sorting results by group columns."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "quantity", "agg_function": "sum", "alias": "total_qty"}],
            sort_results=True,
        )

        result = component.group_data()

        # Results should be sorted alphabetically by category
        categories = [item.data["category"] for item in result]
        assert categories == sorted(categories)

    def test_drop_na_option(self):
        """Test drop_na option for handling null values."""
        data = [
            Data(data={"category": "A", "value": 10}),
            Data(data={"category": None, "value": 20}),
            Data(data={"category": "A", "value": 30}),
        ]

        # With drop_na=True (default)
        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
            drop_na=True,
        )

        result = component.group_data()

        # Should only have category A (None is dropped)
        assert len(result) == 1
        assert result[0].data["category"] == "A"
        assert result[0].data["total"] == 40

    def test_preview_data(self, sample_data):
        """Test get_preview_data returns maximum 100 rows."""
        # Create data with more than 100 rows
        large_data = [Data(data={"id": i, "category": f"Cat_{i % 10}", "value": i}) for i in range(150)]

        component = ETLGroupByComponent(
            data_input=large_data,
            group_by_columns=[{"selected": True, "field_name": "id"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        preview = component.get_preview_data()

        # Should return maximum 100 rows
        assert len(preview) <= 100

    def test_group_stats(self, sample_data):
        """Test get_group_stats returns correct statistics."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "quantity", "agg_function": "sum", "alias": "total_qty"}],
        )

        stats = component.get_group_stats()

        assert stats.data["group_by_columns"] == ["category"]
        assert "quantity_sum" in stats.data["aggregations"][0]
        assert stats.data["total_groups"] == 2
        assert stats.data["input_records"] == 5

    def test_error_no_data(self):
        """Test error when no data is provided."""
        component = ETLGroupByComponent(
            data_input=[],
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        with pytest.raises(ValueError):
            component.group_data()

    def test_error_no_group_columns(self, sample_data):
        """Test error when no group columns are specified."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        with pytest.raises(ValueError):
            component.group_data()

    def test_error_no_aggregations(self, sample_data):
        """Test that group by works without aggregations (returns unique combinations)."""
        # Since aggregations are now optional, this should succeed (not raise an error)
        component = ETLGroupByComponent(
            data_input=sample_data, group_by_columns=[{"selected": True, "field_name": "category"}], aggregations=[]
        )

        # Should not raise error - returns unique categories
        result = component.group_data()
        assert len(result) == 2  # Electronics and Clothing

    def test_error_missing_column(self, sample_data):
        """Test error when group column doesn't exist in data."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "nonexistent_column"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        with pytest.raises(ValueError):
            component.group_data()

    def test_extract_field_names(self, sample_data):
        """Test _extract_field_names helper method."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        field_names = component._extract_field_names(sample_data)

        assert set(field_names) == {"product_id", "category", "quantity", "price"}

    def test_extract_field_names_empty_data(self):
        """Test _extract_field_names with empty data."""
        component = ETLGroupByComponent(
            data_input=[],
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        field_names = component._extract_field_names([])

        assert field_names == []

    def test_backward_compatibility_english_functions(self, sample_data):
        """Test that English function names work for backward compatibility."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "quantity", "agg_function": "sum", "alias": "total_qty"},
                {"field_name": "price", "agg_function": "avg", "alias": "avg_price"},
            ],
        )

        result = component.group_data()

        # Should work even with lowercase English function names
        assert len(result) == 2

    def test_default_alias_generation(self, sample_data):
        """Test that default aliases are generated when not provided."""
        component = ETLGroupByComponent(
            data_input=sample_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "quantity", "agg_function": "sum", "alias": ""},  # Empty alias
                {"field_name": "price", "agg_function": "count"},  # No alias key
            ],
        )

        result = component.group_data()

        # Check that default aliases were used
        first_group = result[0].data

        # Should have auto-generated alias like "quantity_sum"
        assert (
            "quantity_sum" in first_group
            or "quantity_nunique" in first_group.keys()
            or any("quantity" in k for k in first_group.keys())
        )

    @pytest.mark.asyncio
    async def test_update_build_config_no_graph_data(self):
        """Test update_build_config when no graph data is available."""
        component = ETLGroupByComponent(
            data_input=[],
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        build_config = {}

        result = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="group_by_columns", action="analyze_fields"
        )

        # Should return build_config unchanged when no graph data
        assert result == build_config

    def test_median_aggregation(self):
        """Test median aggregation function."""
        data = [
            Data(data={"category": "A", "value": 10}),
            Data(data={"category": "A", "value": 20}),
            Data(data={"category": "A", "value": 30}),
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "median", "alias": "median_value"}],
        )

        result = component.group_data()

        assert result[0].data["median_value"] == 20.0

    def test_std_aggregation(self):
        """Test standard deviation aggregation function."""
        data = [
            Data(data={"category": "A", "value": 10}),
            Data(data={"category": "A", "value": 20}),
            Data(data={"category": "A", "value": 30}),
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "std", "alias": "std_value"}],
        )

        result = component.group_data()

        # Standard deviation of [10, 20, 30] ≈ 10
        assert result[0].data["std_value"] == pytest.approx(10.0, rel=0.01)

    def test_first_last_aggregations(self):
        """Test first and last aggregation functions."""
        data = [
            Data(data={"category": "A", "value": 10, "order": 1}),
            Data(data={"category": "A", "value": 20, "order": 2}),
            Data(data={"category": "A", "value": 30, "order": 3}),
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "value", "agg_function": "first", "alias": "first_value"},
                {"field_name": "value", "agg_function": "last", "alias": "last_value"},
            ],
        )

        result = component.group_data()

        # Note: first/last depend on data order
        assert "first_value" in result[0].data
        assert "last_value" in result[0].data

    def test_groupby_without_aggregations(self):
        """Test group by without aggregations (like SQL DISTINCT)."""
        data = [
            Data(data={"category": "A", "region": "US", "value": 10}),
            Data(data={"category": "A", "region": "US", "value": 20}),  # Duplicate combination
            Data(data={"category": "B", "region": "EU", "value": 30}),
            Data(data={"category": "A", "region": "EU", "value": 40}),
            Data(data={"category": "B", "region": "EU", "value": 50}),  # Duplicate combination
        ]

        component = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "category"}, {"selected": True, "field_name": "region"}],
            aggregations=[],  # 不配置聚合
        )

        result = component.group_data()

        # Should return unique combinations only: (A, US), (B, EU), (A, EU)
        assert len(result) == 3

        # Verify unique combinations
        combinations = {(r.data["category"], r.data["region"]) for r in result}
        assert combinations == {("A", "US"), ("B", "EU"), ("A", "EU")}

        # Should only have group by columns, no aggregation columns
        assert len(result[0].data) == 2
        assert "value" not in result[0].data

    def test_groupby_without_aggregations_single_column(self):
        """Test group by single column without aggregations."""
        data = [
            Data(data={"category": "Electronics"}),
            Data(data={"category": "Clothing"}),
            Data(data={"category": "Electronics"}),  # Duplicate
            Data(data={"category": "Food"}),
            Data(data={"category": "Clothing"}),  # Duplicate
        ]

        component = ETLGroupByComponent(
            data_input=data, group_by_columns=[{"selected": True, "field_name": "category"}], aggregations=[]
        )

        result = component.group_data()

        # Should return 3 unique categories
        assert len(result) == 3

        categories = {r.data["category"] for r in result}
        assert categories == {"Electronics", "Clothing", "Food"}
