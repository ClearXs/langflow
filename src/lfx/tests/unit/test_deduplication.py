"""Unit tests for ETL Deduplication Component

Tests cover:
- Delete mode with basic deduplication
- Delete mode with sorting (ascending/descending)
- Merge mode with field concatenation
- Multi-field grouping
- Preview functionality
- Statistics generation
- Error handling
- Field name extraction
"""

import pytest

from lfx.components.operations.deduplication import ETLDeduplicationComponent
from lfx.schema import Data


class TestETLDeduplicationComponent:
    """Test suite for ETL Deduplication component"""

    @pytest.fixture
    def sample_data(self):
        """Test data with duplicate records"""
        return [
            Data(data={"name": "Alice", "age": 30, "city": "Beijing", "score": 85}),
            Data(data={"name": "Bob", "age": 25, "city": "Shanghai", "score": 90}),
            Data(data={"name": "Alice", "age": 30, "city": "Shenzhen", "score": 95}),  # Duplicate
            Data(data={"name": "Charlie", "age": 35, "city": "Guangzhou", "score": 80}),
            Data(data={"name": "Bob", "age": 25, "city": "Hangzhou", "score": 88}),  # Duplicate
        ]

    def test_delete_mode_basic(self, sample_data):
        """Test delete mode - basic deduplication by name and age"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}, {"field_name": "age"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should have 3 unique records (Alice, Bob, Charlie)
        assert len(result) == 3
        names = sorted([r.data["name"] for r in result])
        assert names == ["Alice", "Bob", "Charlie"]

    def test_delete_mode_single_field(self, sample_data):
        """Test delete mode with single grouping field"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should have 3 unique names
        assert len(result) == 3
        names = sorted([r.data["name"] for r in result])
        assert names == ["Alice", "Bob", "Charlie"]

    def test_delete_mode_with_sorting_asc(self, sample_data):
        """Test delete mode with ascending sort"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="score",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Alice has two records with scores 85 and 95
        # With ascending sort, score=85 should be kept (comes first)
        alice_record = next(r for r in result if r.data["name"] == "Alice")
        assert alice_record.data["score"] == 85
        assert alice_record.data["city"] == "Beijing"

        # Bob has two records with scores 90 and 88
        # With ascending sort, score=88 should be kept
        bob_record = next(r for r in result if r.data["name"] == "Bob")
        assert bob_record.data["score"] == 88
        assert bob_record.data["city"] == "Hangzhou"

    def test_delete_mode_with_sorting_desc(self, sample_data):
        """Test delete mode with descending sort"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="score",
            sort_order="desc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # With descending sort, higher scores come first
        # Alice: score=95 should be kept
        alice_record = next(r for r in result if r.data["name"] == "Alice")
        assert alice_record.data["score"] == 95
        assert alice_record.data["city"] == "Shenzhen"

        # Bob: score=90 should be kept
        bob_record = next(r for r in result if r.data["name"] == "Bob")
        assert bob_record.data["score"] == 90
        assert bob_record.data["city"] == "Shanghai"

    def test_merge_mode_basic(self, sample_data):
        """Test merge mode with field concatenation"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="merge",
            sort_field="",
            sort_order="asc",
            merge_separator="|",
        )

        result = component.deduplicate()

        # Should have 3 records after merging
        assert len(result) == 3

        # Alice's record should have merged city and score fields
        alice_record = next(r for r in result if r.data["name"] == "Alice")
        # City should contain both Beijing and Shenzhen
        assert "Beijing" in alice_record.data["city"]
        assert "Shenzhen" in alice_record.data["city"]
        assert "|" in alice_record.data["city"]

        # Scores should also be merged
        assert "85" in str(alice_record.data["score"])
        assert "95" in str(alice_record.data["score"])

    def test_merge_mode_with_custom_separator(self, sample_data):
        """Test merge mode with custom separator"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="merge",
            sort_field="",
            sort_order="asc",
            merge_separator=", ",  # Custom separator with space
        )

        result = component.deduplicate()

        alice_record = next(r for r in result if r.data["name"] == "Alice")
        # Should use custom separator
        assert ", " in alice_record.data["city"]

    def test_multi_field_grouping(self, sample_data):
        """Test deduplication with multiple grouping fields"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}, {"field_name": "age"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # With name+age combination, should have 3 unique combinations
        assert len(result) == 3

    def test_preview_limit_100(self, sample_data):
        """Test preview functionality limits to 100 rows"""
        # Create larger dataset by repeating sample data
        large_data = sample_data * 40  # 5 * 40 = 200 records

        component = ETLDeduplicationComponent(
            data_input=large_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        preview = component.preview_data()

        # Preview should be limited to 100 rows
        assert len(preview) <= 100

    def test_preview_with_small_dataset(self, sample_data):
        """Test preview with dataset smaller than 100 rows"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        preview = component.preview_data()
        full_result = component.deduplicate()

        # Preview should match full result when data < 100 rows
        assert len(preview) == len(full_result)

    def test_get_stats_delete_mode(self, sample_data):
        """Test statistics generation for delete mode"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        stats = component.get_dedup_stats()

        assert stats.data["original_count"] == 5
        assert stats.data["unique_count"] == 3
        assert stats.data["duplicate_count"] == 2
        assert stats.data["deduplication_rate"] == 40.0  # 2/5 * 100
        assert stats.data["group_by_fields"] == ["name"]
        assert stats.data["dedup_mode"] == "delete"
        assert stats.data["sort_field"] == "None"  # No sort field specified
        assert stats.data["sort_order"] == "asc"

    def test_get_stats_with_sorting(self, sample_data):
        """Test statistics with sort field specified"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="score",
            sort_order="desc",
            merge_separator=",",
        )

        stats = component.get_dedup_stats()

        assert stats.data["sort_field"] == "score"
        assert stats.data["sort_order"] == "desc"

    def test_error_no_data(self):
        """Test error when no input data provided"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        with pytest.raises(ValueError):
            component.deduplicate()

    def test_error_no_group_fields(self, sample_data):
        """Test error when no grouping fields specified"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        with pytest.raises(ValueError):
            component.deduplicate()

    def test_error_empty_group_fields(self, sample_data):
        """Test error when grouping fields are empty strings"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": ""}, {"field_name": "  "}],  # Empty or whitespace only
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        with pytest.raises(ValueError):
            component.deduplicate()

    def test_error_field_not_found(self, sample_data):
        """Test error when specified field doesn't exist in data"""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "non_existent_field"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        with pytest.raises(ValueError):
            component.deduplicate()

    def test_extract_field_names_from_data_objects(self, sample_data):
        """Test field name extraction from Data objects"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        field_names = component._extract_field_names(sample_data)

        assert set(field_names) == {"name", "age", "city", "score"}

    def test_extract_field_names_from_dicts(self):
        """Test field name extraction from plain dict objects"""
        dict_data = [
            {"field1": "value1", "field2": "value2"},
            {"field1": "value3", "field2": "value4"},
        ]

        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        field_names = component._extract_field_names(dict_data)

        assert set(field_names) == {"field1", "field2"}

    def test_extract_field_names_empty_list(self):
        """Test field name extraction from empty list"""
        component = ETLDeduplicationComponent(
            data_input=[],
            group_by_fields=[],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        field_names = component._extract_field_names([])

        assert field_names == []

    def test_status_message_on_success(self, sample_data):
        """Test that status message is set correctly on successful deduplication."""
        component = ETLDeduplicationComponent(
            data_input=sample_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        component.deduplicate()

        # Status should be set (not None or empty)
        assert component.status is not None
        assert len(component.status) > 0

    def test_all_fields_unique(self):
        """Test deduplication when all records are already unique"""
        unique_data = [
            Data(data={"id": 1, "name": "Alice"}),
            Data(data={"id": 2, "name": "Bob"}),
            Data(data={"id": 3, "name": "Charlie"}),
        ]

        component = ETLDeduplicationComponent(
            data_input=unique_data,
            group_by_fields=[{"field_name": "id"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should return all 3 records unchanged
        assert len(result) == 3

        stats = component.get_dedup_stats()
        assert stats.data["duplicate_count"] == 0
        assert stats.data["deduplication_rate"] == 0

    def test_all_fields_duplicate(self):
        """Test deduplication when all records are duplicates"""
        duplicate_data = [
            Data(data={"name": "Alice", "age": 30}),
            Data(data={"name": "Alice", "age": 30}),
            Data(data={"name": "Alice", "age": 30}),
        ]

        component = ETLDeduplicationComponent(
            data_input=duplicate_data,
            group_by_fields=[{"field_name": "name"}],
            dedup_mode="delete",
            sort_field="",
            sort_order="asc",
            merge_separator=",",
        )

        result = component.deduplicate()

        # Should keep only 1 record
        assert len(result) == 1
        assert result[0].data["name"] == "Alice"

        stats = component.get_dedup_stats()
        assert stats.data["duplicate_count"] == 2
        assert stats.data["deduplication_rate"] == pytest.approx(66.67, rel=0.01)
