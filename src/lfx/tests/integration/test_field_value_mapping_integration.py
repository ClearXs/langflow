"""Integration tests for ETLFieldValueMappingComponent with upstream components."""

from unittest.mock import AsyncMock, patch

import pytest

from lfx.components.manipulations.field_value_mapping import ETLFieldValueMappingComponent
from lfx.schema import Data


class TestFieldValueMappingIntegration:
    """Integration tests for Field Value Mapping with upstream data sources."""

    @pytest.mark.asyncio
    async def test_field_analysis_with_table_input(self):
        """Test field analysis button extracts fields from upstream table_input."""
        # Simulate upstream table_input data
        upstream_data = [
            Data(data={"user_id": 1, "gender": "1", "age": 25, "status": "active"}),
            Data(data={"user_id": 2, "gender": "0", "age": 17, "status": "inactive"}),
            Data(data={"user_id": 3, "gender": "1", "age": 70, "status": "pending"}),
        ]

        # Create component instance
        component = ETLFieldValueMappingComponent()

        # Mock the get_upstream_data method to return our test data
        with patch.object(component, "get_upstream_data", new_callable=AsyncMock) as mock_get_upstream:
            mock_get_upstream.return_value = upstream_data

            # Simulate the analyze_fields button click
            build_config = {
                "_graph_data": {"some": "graph_data"},
                "_node_id": "test_node",
                "mapping_rules": {"value": []},
            }

            # Call update_build_config as if the analyze button was clicked
            updated_config = await component.update_build_config(
                build_config=build_config, field_value=None, field_name="mapping_rules", action="analyze_fields"
            )

            # Verify fields were extracted
            assert "mapping_rules" in updated_config
            mapping_rules = updated_config["mapping_rules"]["value"]

            # Should have rules for all fields
            assert len(mapping_rules) == 4  # user_id, gender, age, status

            # Check field names were extracted
            field_names = [rule["input_field"] for rule in mapping_rules]
            assert "user_id" in field_names
            assert "gender" in field_names
            assert "age" in field_names
            assert "status" in field_names

            # Check sample values were included
            gender_rule = next(r for r in mapping_rules if r["input_field"] == "gender")
            assert gender_rule["compare_value"] in ["1", "0"]  # Should have a sample value

    @pytest.mark.asyncio
    async def test_complete_flow_with_table_input(self):
        """Test complete data flow from table_input through field_value_mapping."""
        # Simulate data from table_input component
        table_data = [
            Data(data={"product_id": "P001", "category": "1", "price": 999, "stock": "10"}),
            Data(data={"product_id": "P002", "category": "2", "price": 1500, "stock": "5"}),
            Data(data={"product_id": "P003", "category": "3", "price": 25, "stock": "100"}),
        ]

        # Create field value mapping component with rules
        mapping_component = ETLFieldValueMappingComponent(
            data_input=table_data,
            mapping_rules=[
                {
                    "input_field": "category",
                    "operator": "=",
                    "compare_value": "1",
                    "replacement_value": "Electronics",
                    "output_field": "category_name",
                },
                {
                    "input_field": "category",
                    "operator": "=",
                    "compare_value": "2",
                    "replacement_value": "Computers",
                    "output_field": "category_name",
                },
                {
                    "input_field": "category",
                    "operator": "=",
                    "compare_value": "3",
                    "replacement_value": "Accessories",
                    "output_field": "category_name",
                },
                {
                    "input_field": "price",
                    "operator": ">=",
                    "compare_value": "1000",
                    "replacement_value": "High",
                    "output_field": "price_tier",
                },
                {
                    "input_field": "price",
                    "operator": ">=",
                    "compare_value": "100",
                    "replacement_value": "Medium",
                    "output_field": "price_tier",
                },
                {
                    "input_field": "price",
                    "operator": "<",
                    "compare_value": "100",
                    "replacement_value": "Low",
                    "output_field": "price_tier",
                },
            ],
            enable_script=True,
            script_type="python",
            script_content="""
# Add inventory status based on stock
stock_num = int(row.get('stock', 0))
if stock_num > 50:
    result['inventory_status'] = 'High Stock'
elif stock_num > 10:
    result['inventory_status'] = 'Normal Stock'
else:
    result['inventory_status'] = 'Low Stock'

# Calculate inventory value
result['inventory_value'] = row.get('price', 0) * stock_num
""",
        )

        # Execute the mapping
        result = mapping_component.map_field_values()

        # Verify results
        assert len(result) == 3

        # Check first product (Electronics, High price tier, Normal stock)
        product1 = result[0].data
        assert product1["category_name"] == "Electronics"
        assert product1["price_tier"] == "Medium"  # 999 >= 100 (first match wins)
        assert product1["inventory_status"] == "Low Stock"  # stock=10
        assert product1["inventory_value"] == 9990  # 999 * 10

        # Check second product (Computers, High price tier, Low stock)
        product2 = result[1].data
        assert product2["category_name"] == "Computers"
        assert product2["price_tier"] == "High"  # 1500 >= 1000
        assert product2["inventory_status"] == "Low Stock"  # stock=5
        assert product2["inventory_value"] == 7500  # 1500 * 5

        # Check third product (Accessories, Low price tier, High stock)
        product3 = result[2].data
        assert product3["category_name"] == "Accessories"
        assert product3["price_tier"] == "Low"  # 25 < 100
        assert product3["inventory_status"] == "High Stock"  # stock=100
        assert product3["inventory_value"] == 2500  # 25 * 100

    def test_regex_matching_with_real_data(self):
        """Test regex operator with realistic data patterns."""
        # Simulate data with various ID formats
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"order_id": "ORD-2024-001", "customer": "John"}),
                Data(data={"order_id": "REF-2024-002", "customer": "Alice"}),
                Data(data={"order_id": "ORD-2023-999", "customer": "Bob"}),
                Data(data={"order_id": "SPECIAL-001", "customer": "Charlie"}),
            ],
            mapping_rules=[
                {
                    "input_field": "order_id",
                    "operator": "regex",
                    "compare_value": r"^ORD-\d{4}-\d{3}$",
                    "replacement_value": "Standard Order",
                    "output_field": "order_type",
                },
                {
                    "input_field": "order_id",
                    "operator": "regex",
                    "compare_value": r"^REF-\d{4}-\d{3}$",
                    "replacement_value": "Refund Order",
                    "output_field": "order_type",
                },
                {
                    "input_field": "order_id",
                    "operator": "regex",
                    "compare_value": r"2024",
                    "replacement_value": "Current Year",
                    "output_field": "order_year",
                },
                {
                    "input_field": "order_id",
                    "operator": "regex",
                    "compare_value": r"2023",
                    "replacement_value": "Previous Year",
                    "output_field": "order_year",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 4

        # First order: Standard Order from 2024
        assert result[0].data["order_type"] == "Standard Order"
        assert result[0].data["order_year"] == "Current Year"

        # Second order: Refund Order from 2024
        assert result[1].data["order_type"] == "Refund Order"
        assert result[1].data["order_year"] == "Current Year"

        # Third order: Standard Order from 2023
        assert result[2].data["order_type"] == "Standard Order"
        assert result[2].data["order_year"] == "Previous Year"

        # Fourth order: Special order (no type match)
        assert result[3].data.get("order_type") is None
        assert result[3].data.get("order_year") is None

    def test_combined_operators_priority(self):
        """Test that first matching rule wins when multiple rules could apply."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"score": 95, "name": "Alice"}),
                Data(data={"score": 85, "name": "Bob"}),
                Data(data={"score": 75, "name": "Charlie"}),
                Data(data={"score": 65, "name": "David"}),
            ],
            mapping_rules=[
                # Rules are ordered from highest to lowest threshold
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "90",
                    "replacement_value": "Excellent",
                    "output_field": "grade",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "80",
                    "replacement_value": "Good",
                    "output_field": "grade",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "70",
                    "replacement_value": "Average",
                    "output_field": "grade",
                },
                {
                    "input_field": "score",
                    "operator": ">=",
                    "compare_value": "60",
                    "replacement_value": "Below Average",
                    "output_field": "grade",
                },
                # Additional categorization - should not override grade due to first-match-wins
                {
                    "input_field": "score",
                    "operator": ">",
                    "compare_value": "50",
                    "replacement_value": "Pass",
                    "output_field": "grade",  # Same output field
                },
            ],
        )

        result = component.map_field_values()

        # Verify first-match-wins behavior
        assert result[0].data["grade"] == "Excellent"  # 95 >= 90 (first match)
        assert result[1].data["grade"] == "Good"  # 85 >= 80 (first match)
        assert result[2].data["grade"] == "Average"  # 75 >= 70 (first match)
        assert result[3].data["grade"] == "Below Average"  # 65 >= 60 (first match)

        # The ">50" rule should never apply because earlier rules always match first

    def test_script_error_handling(self):
        """Test that script errors don't crash the component."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"value": 10}),
            ],
            mapping_rules=[],
            enable_script=True,
            script_type="python",
            script_content="""
# This will cause an error
undefined_variable = some_undefined_thing
result['error_field'] = undefined_variable
""",
        )

        # Should not raise exception, just return original data
        result = component.map_field_values()

        assert len(result) == 1
        assert result[0].data["value"] == 10
        assert "error_field" not in result[0].data  # Script failed, field not added

    def test_empty_upstream_data_handling(self):
        """Test handling when upstream provides no data."""
        component = ETLFieldValueMappingComponent(
            data_input=[],
            mapping_rules=[
                {
                    "input_field": "field1",
                    "operator": "=",
                    "compare_value": "value1",
                    "replacement_value": "new_value",
                    "output_field": "field2",
                },
            ],
        )

        result = component.map_field_values()

        # Should handle empty data gracefully
        assert len(result) == 0

    def test_missing_fields_graceful_handling(self):
        """Test that missing fields in data are handled gracefully."""
        component = ETLFieldValueMappingComponent(
            data_input=[
                Data(data={"id": 1, "name": "John"}),  # Missing 'status' field
                Data(data={"id": 2, "name": "Jane", "status": "active"}),
            ],
            mapping_rules=[
                {
                    "input_field": "status",
                    "operator": "=",
                    "compare_value": "active",
                    "replacement_value": "Active User",
                    "output_field": "status_label",
                },
            ],
        )

        result = component.map_field_values()

        assert len(result) == 2

        # First record: missing field, no mapping
        assert "status_label" not in result[0].data

        # Second record: field exists, mapping applied
        assert result[1].data["status_label"] == "Active User"
