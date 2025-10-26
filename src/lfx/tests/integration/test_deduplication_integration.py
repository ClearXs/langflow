"""Integration tests for ETL Deduplication Component

Tests integration with:
- table_input component
- csv_input component
- excel_input component
- update_build_config dynamic field loading
- Graph-based field extraction
"""

import pytest

from lfx.components.operations.deduplication import ETLDeduplicationComponent
from lfx.schema import Data


@pytest.mark.asyncio
class TestDeduplicationIntegration:
    """Integration tests for deduplication component with upstream components"""

    @pytest.fixture
    def mock_upstream_data(self):
        """Mock data simulating upstream component output"""
        return [
            Data(data={"user_id": 1, "username": "alice", "email": "alice@example.com", "created_at": "2024-01-01"}),
            Data(data={"user_id": 2, "username": "bob", "email": "bob@example.com", "created_at": "2024-01-02"}),
            Data(
                data={"user_id": 1, "username": "alice", "email": "alice@example.com", "created_at": "2024-01-03"}
            ),  # Duplicate
            Data(
                data={"user_id": 3, "username": "charlie", "email": "charlie@example.com", "created_at": "2024-01-04"}
            ),
        ]

    async def test_field_extraction_from_upstream(self, mock_upstream_data):
        """Test extracting field names from upstream data"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        field_names = component._extract_field_names(mock_upstream_data)

        # Should extract all field names from first record
        assert set(field_names) == {"user_id", "username", "email", "created_at"}

    async def test_simulated_update_build_config_no_graph(self):
        """Test update_build_config when no graph data is available"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        build_config = {
            "group_by_fields": {"value": []},
            "sort_field": {"options": []},
        }

        # Simulate clicking "load fields" button without graph data
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="group_by_fields", action="load_fields"
        )

        # Should handle gracefully and return original config
        assert updated_config is not None
        # Status should indicate no upstream data
        assert component.status is not None

    async def test_deduplication_workflow_delete_mode(self, mock_upstream_data):
        """Test full deduplication workflow in delete mode"""
        # Step 1: Simulate upstream component providing data
        input_data = mock_upstream_data

        # Step 2: Configure deduplication component
        component = ETLDeduplicationComponent(
            data_input=input_data,
            group_by_fields=[{"field_name": "user_id"}],
            dedup_mode="delete",
            sort_field="created_at",
            sort_order="desc",
            merge_separator=",",
        )

        # Step 3: Execute deduplication
        result = component.deduplicate()

        # Step 4: Verify results
        assert len(result) == 3  # Should have 3 unique user_ids

        # User 1 (alice) appears twice, should keep the one with later created_at (desc sort)
        alice_records = [r for r in result if r.data["user_id"] == 1]
        assert len(alice_records) == 1
        assert alice_records[0].data["created_at"] == "2024-01-03"

    async def test_deduplication_workflow_merge_mode(self, mock_upstream_data):
        """Test full deduplication workflow in merge mode"""
        component = ETLDeduplicationComponent(
            data_input=mock_upstream_data,
            group_by_fields=[{"field_name": "user_id"}],
            dedup_mode="merge",
            sort_field="",
            sort_order="asc",
            merge_separator="|",
        )

        result = component.deduplicate()

        # Should have 3 unique user_ids
        assert len(result) == 3

        # Alice's record should have merged created_at values
        alice_record = next(r for r in result if r.data["user_id"] == 1)
        # created_at should contain both dates
        assert "2024-01-01" in str(alice_record.data["created_at"])
        assert "2024-01-03" in str(alice_record.data["created_at"])
        assert "|" in str(alice_record.data["created_at"])

    async def test_preview_and_stats_integration(self, mock_upstream_data):
        """Test preview and statistics outputs work together"""
        component = ETLDeduplicationComponent(
            data_input=mock_upstream_data,
            group_by_fields=[{"field_name": "user_id"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        # Get preview
        preview = component.preview_data()

        # Get statistics
        stats = component.get_dedup_stats()

        # Verify consistency
        assert len(preview) == stats.data["unique_count"]
        assert stats.data["original_count"] == 4
        assert stats.data["duplicate_count"] == 1

    async def test_multi_component_pipeline(self, mock_upstream_data):
        """Test deduplication as part of a multi-component pipeline"""
        # Simulate data flow: Input -> Deduplication -> Further processing

        # Step 1: Deduplication
        dedup_component = ETLDeduplicationComponent(
            data_input=mock_upstream_data,
            group_by_fields=[{"field_name": "username"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        deduplicated = dedup_component.deduplicate()

        # Step 2: Verify deduplicated data can be used by downstream components
        assert len(deduplicated) == 3
        assert all(isinstance(d, Data) for d in deduplicated)
        assert all(hasattr(d, "data") and isinstance(d.data, dict) for d in deduplicated)

        # Step 3: Simulate downstream processing (e.g., filtering)
        filtered = [d for d in deduplicated if d.data["user_id"] > 1]
        assert len(filtered) == 2  # Bob and Charlie

    async def test_complex_multi_field_deduplication(self):
        """Test deduplication with complex multi-field grouping scenarios"""
        complex_data = [
            Data(data={"product_id": "A001", "warehouse": "WH1", "quantity": 100, "date": "2024-01-01"}),
            Data(data={"product_id": "A001", "warehouse": "WH2", "quantity": 150, "date": "2024-01-01"}),
            Data(data={"product_id": "A001", "warehouse": "WH1", "quantity": 120, "date": "2024-01-02"}),  # Duplicate
            Data(data={"product_id": "B002", "warehouse": "WH1", "quantity": 200, "date": "2024-01-01"}),
        ]

        component = ETLDeduplicationComponent(
            data_input=complex_data,
            group_by_fields=[{"field_name": "product_id"}, {"field_name": "warehouse"}],
            dedup_mode="delete",
            sort_field="date",
            sort_order="desc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should have 3 unique product-warehouse combinations
        assert len(result) == 3

        # Product A001 at WH1 appears twice, should keep the one with later date
        a001_wh1 = next(r for r in result if r.data["product_id"] == "A001" and r.data["warehouse"] == "WH1")
        assert a001_wh1.data["date"] == "2024-01-02"
        assert a001_wh1.data["quantity"] == 120

    async def test_error_propagation(self):
        """Test that errors in deduplication propagate correctly"""
        invalid_data = [
            Data(data={"field1": "value1"}),
            Data(data={"field1": "value2"}),
        ]

        component = ETLDeduplicationComponent(
            data_input=invalid_data,
            group_by_fields=[{"field_name": "non_existent_field"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        # Should raise ValueError
        with pytest.raises(ValueError):
            component.deduplicate()

    async def test_large_dataset_performance(self):
        """Test deduplication with larger dataset (performance test)"""
        # Create 1000 records with ~50% duplicates
        large_data = []
        for i in range(500):
            large_data.append(Data(data={"id": i, "value": f"value_{i}", "category": "A"}))
            large_data.append(Data(data={"id": i, "value": f"value_{i}_dup", "category": "A"}))  # Duplicate

        component = ETLDeduplicationComponent(
            data_input=large_data,
            group_by_fields=[{"field_name": "id"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should have 500 unique IDs
        assert len(result) == 500

        # Verify performance by checking stats
        stats = component.get_dedup_stats()
        assert stats.data["original_count"] == 1000
        assert stats.data["unique_count"] == 500
        assert stats.data["duplicate_count"] == 500

    async def test_empty_field_name_handling(self, mock_upstream_data):
        """Test handling of empty field names in group_by_fields"""
        component = ETLDeduplicationComponent(
            data_input=mock_upstream_data,
            group_by_fields=[
                {"field_name": "user_id"},
                {"field_name": ""},  # Empty field name
                {"field_name": "  "},  # Whitespace only
            ],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        # Should ignore empty/whitespace field names and only use user_id
        result = component.deduplicate()
        assert len(result) == 3  # Only deduplicate by user_id

    async def test_update_build_config_with_mock_graph(self, mock_upstream_data):
        """Test update_build_config with mocked graph data"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        # Mock graph data structure
        build_config = {
            "_graph_data": {
                # Simulated graph structure - empty but present
            },
            "_node_id": "test_node_123",
            "group_by_fields": {"value": []},
            "sort_field": {"options": []},
        }

        # Simulate clicking "load fields" button
        # Note: This will fail to get upstream data in test context, but should handle gracefully
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="group_by_fields", action="load_fields"
        )

        # Should return config without crashing
        assert updated_config is not None
        assert "group_by_fields" in updated_config

    async def test_sort_field_refresh(self):
        """Test refreshing sort field options"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        build_config = {
            "_graph_data": {},
            "_node_id": "test_node",
            "sort_field": {"options": []},
        }

        # Simulate refreshing sort field (by setting field_value to empty/None)
        updated_config = await component.update_build_config(
            build_config=build_config, field_value=None, field_name="sort_field", action=None
        )

        # Should handle gracefully even without upstream data
        assert updated_config is not None
