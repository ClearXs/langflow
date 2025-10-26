"""Integration tests for ETLGroupByComponent with upstream data sources."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from lfx.components.operations.group_by import ETLGroupByComponent
from lfx.schema import Data


class TestGroupByIntegration:
    """Integration tests for Group By component with various data sources."""

    @pytest.fixture
    def sample_csv_file(self):
        """Create a temporary CSV file for testing."""
        data = pd.DataFrame(
            {
                "product_id": ["A", "B", "C", "D", "E"],
                "category": ["Electronics", "Electronics", "Clothing", "Clothing", "Electronics"],
                "quantity": [10, 5, 20, 15, 8],
                "price": [100.0, 200.0, 50.0, 75.0, 150.0],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            data.to_csv(f.name, index=False)
            yield f.name

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_table_input_to_groupby_flow(self, sample_csv_file):
        """Test complete flow: CSV → Table Input → Group By."""
        # Note: This is a simplified integration test
        # In a real integration test, you would:
        # 1. Create a flow graph with table_input and group_by nodes
        # 2. Execute the graph
        # 3. Verify the output

        # For this test, we simulate the data flow manually
        # Step 1: Read CSV data (simulating table_input component)
        df = pd.DataFrame(pd.read_csv(sample_csv_file))
        data_input = [Data(data=row.to_dict()) for _, row in df.iterrows()]

        # Step 2: Group by category and aggregate
        groupby_component = ETLGroupByComponent(
            data_input=data_input,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[
                {"field_name": "quantity", "agg_function": "sum", "alias": "total_quantity"},
                {"field_name": "price", "agg_function": "avg", "alias": "avg_price"},
            ],
        )

        result = groupby_component.group_data()

        # Verify results
        assert len(result) == 2

        result_dict = {item.data["category"]: item.data for item in result}

        # Electronics: 3 items with total qty 23 and avg price 150
        assert result_dict["Electronics"]["total_quantity"] == 23
        assert result_dict["Electronics"]["avg_price"] == pytest.approx(150.0)

        # Clothing: 2 items with total qty 35 and avg price 62.5
        assert result_dict["Clothing"]["total_quantity"] == 35
        assert result_dict["Clothing"]["avg_price"] == pytest.approx(62.5)

    def test_groupby_with_field_extraction(self):
        """Test that group_by can extract fields from upstream data."""
        # Create sample upstream data
        upstream_data = [
            Data(data={"user_id": 1, "product": "A", "amount": 100}),
            Data(data={"user_id": 2, "product": "B", "amount": 200}),
            Data(data={"user_id": 1, "product": "C", "amount": 150}),
        ]

        groupby_component = ETLGroupByComponent(
            data_input=upstream_data,
            group_by_columns=[{"selected": True, "field_name": "user_id"}],
            aggregations=[{"field_name": "amount", "agg_function": "sum", "alias": "total_spent"}],
        )

        # Extract field names
        field_names = groupby_component._extract_field_names(upstream_data)

        assert set(field_names) == {"user_id", "product", "amount"}

        # Execute grouping
        result = groupby_component.group_data()

        assert len(result) == 2

        user1 = next(item for item in result if item.data["user_id"] == 1)
        assert user1.data["total_spent"] == 250  # 100 + 150

    def test_multi_stage_aggregation(self):
        """Test multi-stage aggregation: Group → Filter → Group again."""
        # Initial data
        data = [
            Data(data={"region": "North", "store": "A", "sales": 100}),
            Data(data={"region": "North", "store": "B", "sales": 150}),
            Data(data={"region": "South", "store": "C", "sales": 200}),
            Data(data={"region": "South", "store": "D", "sales": 250}),
            Data(data={"region": "North", "store": "A", "sales": 120}),
        ]

        # Stage 1: Group by region and store
        groupby1 = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "region"}, {"selected": True, "field_name": "store"}],
            aggregations=[{"field_name": "sales", "agg_function": "sum", "alias": "store_total"}],
        )

        stage1_result = groupby1.group_data()

        # Should have 4 groups: (North, A), (North, B), (South, C), (South, D)
        assert len(stage1_result) == 4

        # Stage 2: Group by region only
        groupby2 = ETLGroupByComponent(
            data_input=stage1_result,
            group_by_columns=[{"selected": True, "field_name": "region"}],
            aggregations=[{"field_name": "store_total", "agg_function": "sum", "alias": "region_total"}],
        )

        stage2_result = groupby2.group_data()

        # Should have 2 groups: North, South
        assert len(stage2_result) == 2

        result_dict = {item.data["region"]: item.data for item in stage2_result}

        # North: (100 + 120) + 150 = 370
        assert result_dict["North"]["region_total"] == 370

        # South: 200 + 250 = 450
        assert result_dict["South"]["region_total"] == 450

    def test_groupby_with_count_distinct_integration(self):
        """Test count distinct in a realistic sales scenario."""
        # Sales data with repeated customers
        sales_data = [
            Data(data={"store": "Store1", "customer_id": 101, "product": "Laptop", "amount": 1000}),
            Data(data={"store": "Store1", "customer_id": 101, "product": "Mouse", "amount": 50}),
            Data(data={"store": "Store1", "customer_id": 102, "product": "Laptop", "amount": 1000}),
            Data(data={"store": "Store2", "customer_id": 201, "product": "Phone", "amount": 800}),
            Data(data={"store": "Store2", "customer_id": 202, "product": "Phone", "amount": 800}),
        ]

        groupby = ETLGroupByComponent(
            data_input=sales_data,
            group_by_columns=[{"selected": True, "field_name": "store"}],
            aggregations=[
                {"field_name": "customer_id", "agg_function": "count_distinct", "alias": "unique_customers"},
                {"field_name": "amount", "agg_function": "sum", "alias": "total_sales"},
                {"field_name": "product", "agg_function": "count", "alias": "transaction_count"},
            ],
        )

        result = groupby.group_data()

        result_dict = {item.data["store"]: item.data for item in result}

        # Store1: 2 unique customers, 2050 total sales, 3 transactions
        assert result_dict["Store1"]["unique_customers"] == 2
        assert result_dict["Store1"]["total_sales"] == 2050
        assert result_dict["Store1"]["transaction_count"] == 3

        # Store2: 2 unique customers, 1600 total sales, 2 transactions
        assert result_dict["Store2"]["unique_customers"] == 2
        assert result_dict["Store2"]["total_sales"] == 1600
        assert result_dict["Store2"]["transaction_count"] == 2

    def test_groupby_preview_large_dataset(self):
        """Test preview functionality with large dataset."""
        # Create large dataset (500 unique categories)
        large_data = [Data(data={"category": i, "value": i * 10}) for i in range(500)]

        groupby = ETLGroupByComponent(
            data_input=large_data,
            group_by_columns=[{"selected": True, "field_name": "category"}],
            aggregations=[{"field_name": "value", "agg_function": "sum", "alias": "total"}],
        )

        # Full data should have 500 groups
        full_result = groupby.group_data()
        assert len(full_result) == 500

        # Preview should return max 100 rows
        preview_result = groupby.get_preview_data()
        assert len(preview_result) == 100

    def test_groupby_stats_output(self):
        """Test group statistics output."""
        data = [
            Data(data={"dept": "Sales", "employee": "John", "salary": 50000}),
            Data(data={"dept": "Sales", "employee": "Jane", "salary": 60000}),
            Data(data={"dept": "IT", "employee": "Bob", "salary": 70000}),
        ]

        groupby = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "dept"}],
            aggregations=[{"field_name": "salary", "agg_function": "avg", "alias": "avg_salary"}],
        )

        stats = groupby.get_group_stats()

        assert stats.data["group_by_columns"] == ["dept"]
        assert stats.data["total_groups"] == 2
        assert stats.data["input_records"] == 3
        assert len(stats.data["aggregations"]) > 0

    def test_groupby_with_sorting(self):
        """Test grouping with sorting enabled."""
        data = [
            Data(data={"priority": 3, "tasks": 5}),
            Data(data={"priority": 1, "tasks": 10}),
            Data(data={"priority": 2, "tasks": 7}),
            Data(data={"priority": 1, "tasks": 3}),
        ]

        groupby = ETLGroupByComponent(
            data_input=data,
            group_by_columns=[{"selected": True, "field_name": "priority"}],
            aggregations=[{"field_name": "tasks", "agg_function": "sum", "alias": "total_tasks"}],
            sort_results=True,
        )

        result = groupby.group_data()

        # Results should be sorted by priority (1, 2, 3)
        priorities = [item.data["priority"] for item in result]
        assert priorities == [1, 2, 3]

        # Verify aggregations
        assert result[0].data["total_tasks"] == 13  # Priority 1: 10 + 3
        assert result[1].data["total_tasks"] == 7  # Priority 2: 7
        assert result[2].data["total_tasks"] == 5  # Priority 3: 5

    @pytest.mark.asyncio
    async def test_field_analysis_with_upstream_data(self):
        """Test field analysis functionality with simulated upstream data."""
        # This would require a full graph context in real integration tests
        # For now, we test the field extraction logic

        upstream_data = [
            Data(data={"col1": "A", "col2": 10, "col3": 100.5}),
            Data(data={"col1": "B", "col2": 20, "col3": 200.5}),
        ]

        groupby = ETLGroupByComponent(
            data_input=upstream_data,
            group_by_columns=[{"selected": True, "field_name": "col1"}],
            aggregations=[{"field_name": "col2", "agg_function": "sum", "alias": "total"}],
        )

        # Test field extraction
        fields = groupby._extract_field_names(upstream_data)

        assert set(fields) == {"col1", "col2", "col3"}

    def test_real_world_sales_analysis(self):
        """Test real-world scenario: Sales analysis by product and region."""
        sales_data = [
            Data(data={"product": "Laptop", "region": "US", "units": 100, "revenue": 100000}),
            Data(data={"product": "Laptop", "region": "EU", "units": 80, "revenue": 80000}),
            Data(data={"product": "Phone", "region": "US", "units": 200, "revenue": 160000}),
            Data(data={"product": "Phone", "region": "EU", "units": 150, "revenue": 120000}),
            Data(data={"product": "Laptop", "region": "US", "units": 50, "revenue": 50000}),
        ]

        # Analysis 1: Total by product
        product_analysis = ETLGroupByComponent(
            data_input=sales_data,
            group_by_columns=[{"selected": True, "field_name": "product"}],
            aggregations=[
                {"field_name": "units", "agg_function": "sum", "alias": "total_units"},
                {"field_name": "revenue", "agg_function": "sum", "alias": "total_revenue"},
            ],
        )

        product_result = product_analysis.group_data()
        product_dict = {item.data["product"]: item.data for item in product_result}

        assert product_dict["Laptop"]["total_units"] == 230  # 100 + 80 + 50
        assert product_dict["Laptop"]["total_revenue"] == 230000

        assert product_dict["Phone"]["total_units"] == 350  # 200 + 150
        assert product_dict["Phone"]["total_revenue"] == 280000

        # Analysis 2: By product and region
        detailed_analysis = ETLGroupByComponent(
            data_input=sales_data,
            group_by_columns=[{"selected": True, "field_name": "product"}, {"selected": True, "field_name": "region"}],
            aggregations=[
                {"field_name": "units", "agg_function": "sum", "alias": "total_units"},
                {"field_name": "revenue", "agg_function": "avg", "alias": "avg_revenue_per_sale"},
            ],
            sort_results=True,
        )

        detailed_result = detailed_analysis.group_data()

        # Should have 4 groups
        assert len(detailed_result) == 4

        # Find Laptop in US
        laptop_us = next(
            item for item in detailed_result if item.data["product"] == "Laptop" and item.data["region"] == "US"
        )
        assert laptop_us.data["total_units"] == 150  # 100 + 50
