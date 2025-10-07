import pytest
import json
from unittest.mock import Mock
from lfx.components.data.deduplicator import DeduplicatorComponent
from langflow.schema import Data


class TestDeduplicatorComponent:

    @pytest.fixture
    def component(self):
        return DeduplicatorComponent()

    @pytest.fixture
    def sample_data(self):
        return [
            Data(data={"id": 1, "name": "John", "email": "john@example.com", "age": 25}),
            Data(data={"id": 2, "name": "Jane", "email": "jane@example.com", "age": 30}),
            Data(data={"id": 3, "name": "John", "email": "john@example.com", "age": 25}),  # duplicate
            Data(data={"id": 4, "name": "Bob", "email": "bob@example.com", "age": 35}),
            Data(data={"id": 5, "name": "jane", "email": "JANE@example.com", "age": 30}),  # potential duplicate
        ]

    def test_full_record_deduplication(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "full_record"
        component.case_sensitive = True

        result = component.deduplicate_data()

        assert len(result.data) == 4  # Should remove exact duplicate
        assert result.data[0].data["id"] == 1
        assert result.data[1].data["id"] == 2
        assert result.data[2].data["id"] == 4
        assert result.data[3].data["id"] == 5

    def test_key_fields_deduplication(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name", "email"]'
        component.case_sensitive = False

        result = component.deduplicate_data()

        assert len(result.data) == 3  # Should remove duplicates based on name+email
        names = [item.data["name"] for item in result.data]
        assert "John" in names
        assert len([n for n in names if n.lower() == "jane"]) == 1  # Only one Jane variant

    def test_custom_hash_deduplication(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "custom_hash"
        component.hash_fields = '["email"]'
        component.case_sensitive = False

        result = component.deduplicate_data()

        assert len(result.data) == 3  # Should deduplicate based on email hash
        emails = [item.data["email"].lower() for item in result.data]
        assert len(set(emails)) == len(emails)  # All unique emails

    def test_keep_strategy_first(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name", "email"]'
        component.keep_strategy = "first"
        component.case_sensitive = False

        result = component.deduplicate_data()

        # Should keep the first occurrence of each duplicate group
        john_record = next(item for item in result.data if item.data["name"] == "John")
        assert john_record.data["id"] == 1  # First John

        jane_record = next(item for item in result.data if item.data["name"] == "Jane")
        assert jane_record.data["id"] == 2  # First Jane

    def test_keep_strategy_last(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name", "email"]'
        component.keep_strategy = "last"
        component.case_sensitive = False

        result = component.deduplicate_data()

        # Should keep the last occurrence of each duplicate group
        jane_record = next(item for item in result.data if item.data["name"].lower() == "jane")
        assert jane_record.data["id"] == 5  # Last Jane variant

    def test_most_complete_strategy(self, component):
        # Create data with varying completeness
        data_with_nulls = [
            Data(data={"id": 1, "name": "John", "email": "john@example.com", "age": None}),
            Data(data={"id": 2, "name": "John", "email": "john@example.com", "age": 25, "city": "NYC"}),
            Data(data={"id": 3, "name": "Jane", "email": None, "age": 30}),
            Data(data={"id": 4, "name": "Jane", "email": "jane@example.com", "age": 30}),
        ]

        component.data = data_with_nulls
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name"]'
        component.keep_strategy = "most_complete"

        result = component.deduplicate_data()

        assert len(result.data) == 2

        # John with more complete data should be kept
        john_record = next(item for item in result.data if item.data["name"] == "John")
        assert john_record.data["id"] == 2  # Has city field

        # Jane with email should be kept
        jane_record = next(item for item in result.data if item.data["name"] == "Jane")
        assert jane_record.data["id"] == 4  # Has email

    def test_preserve_order(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "full_record"
        component.preserve_order = True

        result = component.deduplicate_data()

        # Check that order is preserved (original IDs should be in ascending order)
        ids = [item.data["id"] for item in result.data]
        assert ids == sorted(ids)

    def test_ignore_whitespace(self, component):
        data_with_whitespace = [
            Data(data={"id": 1, "name": " John ", "email": "john@example.com"}),
            Data(data={"id": 2, "name": "John", "email": " john@example.com "}),
            Data(data={"id": 3, "name": "Jane", "email": "jane@example.com"}),
        ]

        component.data = data_with_whitespace
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name", "email"]'
        component.ignore_whitespace = True

        result = component.deduplicate_data()

        assert len(result.data) == 2  # Should treat whitespace variants as duplicates

    def test_duplicate_report(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name", "email"]'
        component.include_duplicate_info = True
        component.case_sensitive = False

        # Run deduplication first
        component.deduplicate_data()

        # Get duplicate report
        report = component.get_duplicate_report()

        assert "total_records" in report.data
        assert "unique_records" in report.data
        assert "duplicate_records" in report.data
        assert "duplicate_groups" in report.data

        assert report.data["total_records"] == 5
        assert report.data["unique_records"] == 3
        assert report.data["duplicate_records"] == 2

    def test_duplicate_records_output(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "full_record"

        # Run deduplication first
        component.deduplicate_data()

        # Get duplicate records
        duplicates = component.get_duplicate_records()

        assert len(duplicates.data) == 1  # Only one exact duplicate
        assert duplicates.data[0].data["id"] == 3  # The duplicate John record

    def test_empty_data_handling(self, component):
        component.data = []

        with pytest.raises(ValueError, match="empty"):
            component.deduplicate_data()

    def test_invalid_json_key_fields(self, component, sample_data):
        component.data = sample_data
        component.dedup_strategy = "key_fields"
        component.key_fields = "invalid json"

        with pytest.raises(json.JSONDecodeError):
            component.deduplicate_data()

    def test_single_record(self, component):
        single_data = [Data(data={"id": 1, "name": "John"})]
        component.data = single_data
        component.dedup_strategy = "full_record"

        result = component.deduplicate_data()

        assert len(result.data) == 1
        assert result.data[0].data["id"] == 1

    def test_fuzzy_matching_strategy(self, component):
        fuzzy_data = [
            Data(data={"id": 1, "name": "John Smith", "email": "john@example.com"}),
            Data(data={"id": 2, "name": "Jon Smith", "email": "jon@example.com"}),  # Similar
            Data(data={"id": 3, "name": "Jane Doe", "email": "jane@example.com"}),
            Data(data={"id": 4, "name": "John Smyth", "email": "johnsmyth@example.com"}),  # Similar
        ]

        component.data = fuzzy_data
        component.dedup_strategy = "fuzzy_match"
        component.fuzzy_config = '{"threshold": 0.8, "fields": ["name"]}'

        result = component.deduplicate_data()

        # Should identify similar names as duplicates
        assert len(result.data) <= 3  # Depending on fuzzy matching results

    def test_custom_priority_keep_strategy(self, component):
        priority_data = [
            Data(data={"id": 1, "name": "John", "priority": 1, "score": 80}),
            Data(data={"id": 2, "name": "John", "priority": 2, "score": 90}),
            Data(data={"id": 3, "name": "John", "priority": 3, "score": 85}),
        ]

        component.data = priority_data
        component.dedup_strategy = "key_fields"
        component.key_fields = '["name"]'
        component.keep_strategy = "custom_priority"
        component.priority_fields = '["score", "priority"]'

        result = component.deduplicate_data()

        assert len(result.data) == 1
        # Should keep the record with highest score
        assert result.data[0].data["id"] == 2
        assert result.data[0].data["score"] == 90