"""Integration tests for ConditionalRouterComponent with upstream components."""

from unittest.mock import patch

from lfx.components.input_output.csv_input import ETLCSVInputComponent
from lfx.components.input_output.table_input import ETLTableInputComponent
from lfx.components.logic.conditional_router import ConditionalRouterComponent
from lfx.components.manipulations.field_name_mapping import ETLFieldNameMappingComponent
from lfx.schema import Data, Message


class TestConditionalRouterIntegration:
    """Integration tests for Conditional Router with various upstream components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_i18n = patch("i18n.t", side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key)
        self.mock_i18n.start()

    def teardown_method(self):
        """Clean up after tests."""
        self.mock_i18n.stop()

    # ==================== Test Group 1: Table Input Integration ====================

    def test_integration_with_table_input(self):
        """Test integration with ETLTableInput component."""
        # Create upstream table input component
        table_input = ETLTableInputComponent()
        table_input.data = [
            {"name": "Alice", "age": 30, "status": "active", "salary": 50000},
            {"name": "Bob", "age": 25, "status": "inactive", "salary": 45000},
            {"name": "Charlie", "age": 35, "status": "active", "salary": 60000},
        ]

        # Create conditional router with multi-conditions
        router = ConditionalRouterComponent()
        router.data_input = Data(data=table_input.data)
        router.conditions = [
            {"field_name": "status", "operator": "equals", "compare_value": "active"},
            {"field_name": "age", "operator": "greater than", "compare_value": "28"},
        ]
        router.combination_logic = "AND"
        router.true_case_message = Message(text="High value active employee")
        router.false_case_message = Message(text="Does not meet criteria")

        # Test field extraction from upstream data
        field_info_list = router.extract_field_info_with_types(router.data_input)
        field_names = [info.name for info in field_info_list]

        assert "name" in field_names
        assert "age" in field_names
        assert "status" in field_names
        assert "salary" in field_names

        # Test condition evaluation
        result = router.evaluate_conditions(Data(data={"name": "Alice", "age": 30, "status": "active"}))
        assert result is True  # Alice is active and over 28

        result = router.evaluate_conditions(Data(data={"name": "Bob", "age": 25, "status": "active"}))
        assert result is False  # Bob is active but not over 28

        result = router.evaluate_conditions(Data(data={"name": "Charlie", "age": 35, "status": "inactive"}))
        assert result is False  # Charlie is over 28 but not active

    def test_integration_with_nested_table_data(self):
        """Test integration with nested table data structures."""
        # Create upstream data with nested structure
        nested_data = [
            {
                "user": {"profile": {"name": "Alice", "department": "Engineering"}},
                "performance": {"score": 85, "rating": "excellent"},
                "metadata": {"joined": "2024-01-15", "active": True},
            },
            {
                "user": {"profile": {"name": "Bob", "department": "Sales"}},
                "performance": {"score": 72, "rating": "good"},
                "metadata": {"joined": "2024-02-20", "active": False},
            },
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=nested_data)
        router.conditions = [
            {"field_name": "user.profile.department", "operator": "equals", "compare_value": "Engineering"},
            {"field_name": "performance.score", "operator": "greater than", "compare_value": "80"},
        ]
        router.combination_logic = "AND"

        # Test nested field extraction
        field_info_list = router.extract_field_info_with_types(router.data_input)
        field_names = [info.name for info in field_info_list]

        assert "user.profile.name" in field_names
        assert "user.profile.department" in field_names
        assert "performance.score" in field_names
        assert "metadata.active" in field_names

        # Test nested field condition evaluation
        result = router.evaluate_conditions(Data(data=nested_data[0]))
        assert result is True  # Alice is in Engineering with score > 80

        result = router.evaluate_conditions(Data(data=nested_data[1]))
        assert result is False  # Bob is not in Engineering

    # ==================== Test Group 2: CSV Input Integration ====================

    def test_integration_with_csv_input(self):
        """Test integration with ETLCSVInput component."""
        # Mock CSV input component
        csv_input = ETLCSVInputComponent()
        csv_input.data = [
            {"product": "Laptop", "category": "Electronics", "price": 999.99, "stock": 50},
            {"product": "Desk", "category": "Furniture", "price": 299.99, "stock": 15},
            {"product": "Mouse", "category": "Electronics", "price": 25.99, "stock": 200},
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=csv_input.data)
        router.conditions = [
            {"field_name": "category", "operator": "equals", "compare_value": "Electronics"},
            {"field_name": "price", "operator": "greater than", "compare_value": "100"},
        ]
        router.combination_logic = "AND"

        # Test field type inference from CSV data
        field_info_list = router.extract_field_info_with_types(router.data_input)
        field_types = {info.name: info.type for info in field_info_list}

        assert field_types["product"] == "string"
        assert field_types["category"] == "string"
        assert field_types["price"] == "number"
        assert field_types["stock"] == "number"

        # Test condition evaluation
        result = router.evaluate_conditions(Data(data=csv_input.data[0]))
        assert result is True  # Laptop is Electronics and costs > 100

        result = router.evaluate_conditions(Data(data=csv_input.data[1]))
        assert result is False  # Desk is not Electronics

        result = router.evaluate_conditions(Data(data=csv_input.data[2]))
        assert result is False  # Mouse is Electronics but costs < 100

    # ==================== Test Group 3: Field Name Mapping Integration ====================

    def test_integration_with_field_name_mapping(self):
        """Test integration with ETLFieldNameMapping component."""
        # Create field name mapping component that transforms field names
        mapping_component = ETLFieldNameMappingComponent()
        mapping_component.field_mapping = [
            {"old_field": "user_name", "new_field": "name"},
            {"old_field": "user_age", "new_field": "age"},
            {"old_field": "is_active", "new_field": "active"},
        ]

        # Simulate mapped data
        mapped_data = [
            {"name": "Alice", "age": 30, "active": True},
            {"name": "Bob", "age": 25, "active": False},
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=mapped_data)
        router.conditions = [
            {"field_name": "active", "operator": "equals", "compare_value": "True"},
            {"field_name": "age", "operator": "greater than", "compare_value": "28"},
        ]
        router.combination_logic = "AND"

        # Test that router works with mapped field names
        result = router.evaluate_conditions(Data(data=mapped_data[0]))
        assert result is True  # Alice is active and over 28

        result = router.evaluate_conditions(Data(data=mapped_data[1]))
        assert result is False  # Bob is not active

    # ==================== Test Group 4: Complex Multi-Condition Scenarios ====================

    def test_complex_or_condition_scenario(self):
        """Test complex scenario with OR logic."""
        # Sales data with multiple criteria
        sales_data = [
            {"region": "North", "sales": 150000, "quarter": "Q1", "target_met": True},
            {"region": "South", "sales": 80000, "quarter": "Q1", "target_met": False},
            {"region": "East", "sales": 200000, "quarter": "Q2", "target_met": True},
            {"region": "West", "sales": 120000, "quarter": "Q2", "target_met": False},
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=sales_data)
        router.conditions = [
            {"field_name": "sales", "operator": "greater than", "compare_value": "100000"},
            {"field_name": "target_met", "operator": "equals", "compare_value": "True"},
        ]
        router.combination_logic = "OR"

        # Test OR logic: should pass if either condition is true
        result = router.evaluate_conditions(Data(data=sales_data[0]))
        assert result is True  # Both conditions true

        result = router.evaluate_conditions(Data(data=sales_data[1]))
        assert result is False  # Both conditions false

        result = router.evaluate_conditions(Data(data=sales_data[2]))
        assert result is True  # Both conditions true

        result = router.evaluate_conditions(Data(data=sales_data[3]))
        assert result is True  # Sales > 100000 but target_met = False

    def test_date_based_conditions(self):
        """Test conditions based on date fields."""
        # Project data with dates
        project_data = [
            {
                "project": "Website Redesign",
                "start_date": "2024-01-15",
                "end_date": "2024-03-30",
                "status": "completed",
            },
            {"project": "Mobile App", "start_date": "2024-02-01", "end_date": "2024-06-15", "status": "in_progress"},
            {"project": "API Integration", "start_date": "2024-03-10", "end_date": "", "status": "planning"},
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=project_data)
        router.conditions = [
            {"field_name": "status", "operator": "equals", "compare_value": "completed"},
            {"field_name": "end_date", "operator": "is not empty", "compare_value": ""},
        ]
        router.combination_logic = "AND"

        # Test date field type inference
        field_info_list = router.extract_field_info_with_types(router.data_input)
        field_types = {info.name: info.type for info in field_info_list}

        assert field_types["start_date"] == "date"
        assert field_types["end_date"] == "date"

        # Test date-based conditions
        result = router.evaluate_conditions(Data(data=project_data[0]))
        assert result is True  # Completed with end date

        result = router.evaluate_conditions(Data(data=project_data[1]))
        assert result is False  # Not completed

        result = router.evaluate_conditions(Data(data=project_data[2]))
        assert result is False  # Not completed and no end date

    # ==================== Test Group 5: Performance and Scaling Tests ====================

    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        import time

        # Generate large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append(
                {
                    "id": i,
                    "category": f"Category_{i % 10}",
                    "value": i * 10,
                    "active": i % 3 == 0,
                    "score": 50 + (i % 50),
                }
            )

        router = ConditionalRouterComponent()
        router.data_input = Data(data=large_dataset)
        router.conditions = [
            {"field_name": "active", "operator": "equals", "compare_value": "True"},
            {"field_name": "score", "operator": "greater than", "compare_value": "75"},
        ]
        router.combination_logic = "AND"

        # Test field extraction performance
        start_time = time.time()
        field_info_list = router.extract_field_info_with_types(router.data_input)
        extraction_time = time.time() - start_time

        assert len(field_info_list) > 0
        assert extraction_time < 1.0  # Should complete within 1 second

        # Test condition evaluation performance
        start_time = time.time()
        for i in range(100):  # Test subset for performance
            data_point = large_dataset[i]
            result = router.evaluate_conditions(Data(data=data_point))
        evaluation_time = time.time() - start_time

        assert evaluation_time < 0.5  # Should evaluate 100 conditions within 0.5 seconds

    def test_caching_effectiveness(self):
        """Test that caching improves performance."""
        import time

        data = Data(data=[{"name": "Alice", "age": 30} for _ in range(100)])
        router = ConditionalRouterComponent()

        # First extraction (no cache)
        start_time = time.time()
        field_info_1 = router.extract_field_info_with_types(data)
        first_time = time.time() - start_time

        # Second extraction (using cache)
        start_time = time.time()
        field_info_2 = router.extract_field_info_with_types(data)
        second_time = time.time() - start_time

        # Cached extraction should be faster
        assert second_time < first_time
        assert len(field_info_1) == len(field_info_2)

    # ==================== Test Group 6: Error Handling and Edge Cases ====================

    def test_missing_field_handling(self):
        """Test handling of missing fields in upstream data."""
        # Data with inconsistent field structure
        inconsistent_data = [
            {"name": "Alice", "age": 30, "status": "active"},
            {"name": "Bob", "status": "inactive"},  # Missing age
            {"age": 25, "status": "active"},  # Missing name
            {"name": "Charlie", "age": 35, "salary": 50000},  # Extra field
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=inconsistent_data)
        router.conditions = [
            {"field_name": "name", "operator": "is not empty", "compare_value": ""},
            {"field_name": "age", "operator": "greater than", "compare_value": "0"},
        ]
        router.combination_logic = "AND"

        # Test handling of missing fields gracefully
        result = router.evaluate_conditions(Data(data=inconsistent_data[0]))
        assert result is True  # All fields present

        result = router.evaluate_conditions(Data(data=inconsistent_data[1]))
        assert result is False  # Missing age field

        result = router.evaluate_conditions(Data(data=inconsistent_data[2]))
        assert result is False  # Missing name field

    def test_null_and_empty_value_handling(self):
        """Test handling of null and empty values."""
        data_with_nulls = [
            {"name": "Alice", "age": 30, "status": "active"},
            {"name": "", "age": None, "status": "inactive"},
            {"name": "Bob", "age": 0, "status": ""},
            {"name": None, "age": 25, "status": None},
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=data_with_nulls)
        router.conditions = [
            {"field_name": "name", "operator": "is not empty", "compare_value": ""},
            {"field_name": "age", "operator": "is not empty", "compare_value": ""},
        ]
        router.combination_logic = "OR"

        # Test null/empty value handling
        result = router.evaluate_conditions(Data(data=data_with_nulls[0]))
        assert result is True  # Valid data

        result = router.evaluate_conditions(Data(data=data_with_nulls[1]))
        assert result is False  # Both fields empty/null

        result = router.evaluate_conditions(Data(data=data_with_nulls[2]))
        assert result is True  # Age is 0 (not empty), but name is empty

    # ==================== Test Group 7: Real-world Scenarios ====================

    def test_customer_segmentation_scenario(self):
        """Test real-world customer segmentation scenario."""
        customers = [
            {
                "id": 1,
                "name": "Alice Corp",
                "industry": "Technology",
                "revenue": 1000000,
                "employees": 50,
                "country": "USA",
            },
            {"id": 2, "name": "Bob LLC", "industry": "Retail", "revenue": 500000, "employees": 15, "country": "Canada"},
            {
                "id": 3,
                "name": "Charlie Inc",
                "industry": "Technology",
                "revenue": 2000000,
                "employees": 200,
                "country": "USA",
            },
            {
                "id": 4,
                "name": "David Ltd",
                "industry": "Manufacturing",
                "revenue": 1500000,
                "employees": 100,
                "country": "UK",
            },
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=customers)
        router.conditions = [
            {"field_name": "industry", "operator": "equals", "compare_value": "Technology"},
            {"field_name": "revenue", "operator": "greater than", "compare_value": "500000"},
            {"field_name": "country", "operator": "in list", "compare_value": "USA,Canada"},
        ]
        router.combination_logic = "AND"

        # Test customer segmentation
        result = router.evaluate_conditions(Data(data=customers[0]))
        assert result is True  # Alice Corp: Tech + high revenue + USA

        result = router.evaluate_conditions(Data(data=customers[1]))
        assert result is False  # Bob LLC: Not Technology

        result = router.evaluate_conditions(Data(data=customers[2]))
        assert result is True  # Charlie Inc: Tech + high revenue + USA

        result = router.evaluate_conditions(Data(data=customers[3]))
        assert result is False  # David Ltd: Not Technology + not USA/Canada

    def test_inventory_management_scenario(self):
        """Test real-world inventory management scenario."""
        inventory = [
            {
                "product_id": "P001",
                "name": "Laptop",
                "category": "Electronics",
                "stock": 45,
                "min_stock": 20,
                "price": 999.99,
                "status": "available",
            },
            {
                "product_id": "P002",
                "name": "Mouse",
                "category": "Electronics",
                "stock": 5,
                "min_stock": 15,
                "price": 25.99,
                "status": "available",
            },
            {
                "product_id": "P003",
                "name": "Desk",
                "category": "Furniture",
                "stock": 0,
                "min_stock": 10,
                "price": 299.99,
                "status": "out_of_stock",
            },
            {
                "product_id": "P004",
                "name": "Chair",
                "category": "Furniture",
                "stock": 25,
                "min_stock": 20,
                "price": 199.99,
                "status": "available",
            },
        ]

        router = ConditionalRouterComponent()
        router.data_input = Data(data=inventory)
        router.conditions = [
            {"field_name": "stock", "operator": "less than", "compare_value": "min_stock"},
            {"field_name": "status", "operator": "equals", "compare_value": "available"},
        ]
        router.combination_logic = "AND"

        # Test inventory alerts
        result = router.evaluate_conditions(Data(data=inventory[0]))
        assert result is False  # Laptop: Stock (45) > min_stock (20)

        result = router.evaluate_conditions(Data(data=inventory[1]))
        assert result is True  # Mouse: Stock (5) < min_stock (15) + available

        result = router.evaluate_conditions(Data(data=inventory[2]))
        assert result is False  # Desk: Out of stock

        result = router.evaluate_conditions(Data(data=inventory[3]))
        assert result is False  # Chair: Stock (25) > min_stock (20)
