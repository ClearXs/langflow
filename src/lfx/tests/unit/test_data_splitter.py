import pytest
import json
from lfx.components.data.data_splitter import DataSplitterComponent
from langflow.schema import Data


class TestDataSplitterComponent:

    @pytest.fixture
    def component(self):
        return DataSplitterComponent()

    @pytest.fixture
    def sample_data(self):
        return [
            Data(data={"id": 1, "category": "A", "value": 10}),
            Data(data={"id": 2, "category": "B", "value": 20}),
            Data(data={"id": 3, "category": "A", "value": 30}),
            Data(data={"id": 4, "category": "C", "value": 40}),
            Data(data={"id": 5, "category": "B", "value": 50}),
            Data(data={"id": 6, "category": "A", "value": 60}),
            Data(data={"id": 7, "category": "C", "value": 70}),
            Data(data={"id": 8, "category": "B", "value": 80}),
            Data(data={"id": 9, "category": "A", "value": 90}),
            Data(data={"id": 10, "category": "C", "value": 100}),
        ]

    def test_ratio_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.6, 0.3, 0.1]'  # 60%, 30%, 10%

        result = component.split_data()

        # Check that splits have approximately correct sizes
        assert len(result.data) == 3  # Three splits
        total_records = sum(len(split["data"]) for split in result.data)
        assert total_records == 10  # All records accounted for

        # Check approximate ratios (allowing for rounding)
        assert 5 <= len(result.data[0]["data"]) <= 7  # ~60% of 10
        assert 2 <= len(result.data[1]["data"]) <= 4  # ~30% of 10
        assert 0 <= len(result.data[2]["data"]) <= 2  # ~10% of 10

    def test_random_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "random"
        component.split_ratios = '[0.5, 0.5]'
        component.random_seed = 42  # For reproducibility

        result1 = component.split_data()

        # Reset and split again with same seed
        component.data = sample_data
        result2 = component.split_data()

        # Results should be identical due to same seed
        assert len(result1.data) == len(result2.data)
        for i in range(len(result1.data)):
            assert len(result1.data[i]["data"]) == len(result2.data[i]["data"])

    def test_sequential_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "sequential"
        component.split_ratios = '[0.4, 0.6]'  # 40%, 60%

        result = component.split_data()

        assert len(result.data) == 2
        # Sequential should maintain order
        first_split_ids = [item["id"] for item in result.data[0]["data"]]
        second_split_ids = [item["id"] for item in result.data[1]["data"]]

        # IDs should be in order and non-overlapping
        assert all(id1 < id2 for id1, id2 in zip(first_split_ids[:-1], first_split_ids[1:]))
        assert all(id1 < id2 for id1, id2 in zip(second_split_ids[:-1], second_split_ids[1:]))
        assert max(first_split_ids) < min(second_split_ids)

    def test_conditional_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "conditional"
        component.split_conditions = '''[
            {"condition": "value >= 50", "name": "high_value"},
            {"condition": "value < 50", "name": "low_value"}
        ]'''

        result = component.split_data()

        assert len(result.data) == 2

        # Find high and low value splits
        high_split = next(split for split in result.data if split["name"] == "high_value")
        low_split = next(split for split in result.data if split["name"] == "low_value")

        # Check conditions are met
        for item in high_split["data"]:
            assert item["value"] >= 50

        for item in low_split["data"]:
            assert item["value"] < 50

    def test_field_value_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "field_value"
        component.split_field = "category"

        result = component.split_data()

        # Should have one split per unique category value
        categories = set(item.data["category"] for item in sample_data)
        assert len(result.data) == len(categories)

        # Each split should contain only records with the same category
        for split in result.data:
            split_categories = set(item["category"] for item in split["data"])
            assert len(split_categories) == 1  # Only one unique category per split

    def test_chunk_size_splitting(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "chunk_size"
        component.chunk_size = 3

        result = component.split_data()

        # Should have ceil(10/3) = 4 chunks
        assert len(result.data) == 4

        # First 3 chunks should have 3 items each
        for i in range(3):
            assert len(result.data[i]["data"]) == 3

        # Last chunk should have 1 item
        assert len(result.data[3]["data"]) == 1

    def test_stratified_sampling(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.7, 0.3]'
        component.stratify_field = "category"

        result = component.split_data()

        # Each split should maintain approximately the same category distribution
        original_category_counts = {}
        for item in sample_data:
            cat = item.data["category"]
            original_category_counts[cat] = original_category_counts.get(cat, 0) + 1

        for split in result.data:
            split_category_counts = {}
            for item in split["data"]:
                cat = item["category"]
                split_category_counts[cat] = split_category_counts.get(cat, 0) + 1

            # Check that proportions are maintained (allowing for rounding)
            for cat in original_category_counts:
                if cat in split_category_counts:
                    original_prop = original_category_counts[cat] / len(sample_data)
                    split_prop = split_category_counts[cat] / len(split["data"])
                    # Allow some tolerance for rounding
                    assert abs(original_prop - split_prop) <= 0.2

    def test_shuffle_data(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[1.0]'  # Single split to test shuffling
        component.shuffle_data = True
        component.random_seed = 42

        result = component.split_data()

        # With shuffling, order should likely be different
        original_ids = [item.data["id"] for item in sample_data]
        shuffled_ids = [item["id"] for item in result.data[0]["data"]]

        # Note: There's a small chance they could be the same, but very unlikely
        # For a more robust test, we could check multiple shuffles
        assert len(original_ids) == len(shuffled_ids)
        assert set(original_ids) == set(shuffled_ids)  # Same elements

    def test_preserve_order(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.5, 0.5]'
        component.preserve_order = True
        component.shuffle_data = False

        result = component.split_data()

        # Within each split, order should be preserved
        for split in result.data:
            ids = [item["id"] for item in split["data"]]
            assert ids == sorted(ids)  # Should be in ascending order

    def test_include_remainder(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.3, 0.3]'  # Only 60%, leaving 40% remainder
        component.include_remainder = True

        result = component.split_data()

        # Should have 3 splits (2 specified + 1 remainder)
        assert len(result.data) == 3

        total_records = sum(len(split["data"]) for split in result.data)
        assert total_records == 10  # All records included

    def test_subset_names(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.6, 0.2, 0.2]'
        component.subset_names = '["train", "validation", "test"]'

        result = component.split_data()

        # Check that splits have the correct names
        names = [split["name"] for split in result.data]
        assert "train" in names
        assert "validation" in names
        assert "test" in names

    def test_output_format_combined(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.7, 0.3]'
        component.output_format = "combined"

        result = component.split_data()

        # Combined format should include split information in each record
        for split in result.data:
            for item in split["data"]:
                assert "split_index" in item or "split_name" in item

    def test_split_report(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.6, 0.4]'

        # Run splitting first
        component.split_data()

        # Get split report
        report = component.get_split_report()

        assert "total_records" in report.data
        assert "number_of_splits" in report.data
        assert "split_sizes" in report.data
        assert "split_strategy" in report.data

        assert report.data["total_records"] == 10
        assert report.data["number_of_splits"] == 2

    def test_subset_info_output(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "field_value"
        component.split_field = "category"

        # Run splitting first
        component.split_data()

        # Get subset info
        info = component.get_subset_info()

        assert "subset_details" in info.data
        subset_details = info.data["subset_details"]

        # Should have info for each category
        categories = set(item.data["category"] for item in sample_data)
        assert len(subset_details) == len(categories)

    def test_empty_data_handling(self, component):
        component.data = []

        with pytest.raises(ValueError, match="empty"):
            component.split_data()

    def test_invalid_ratios_sum(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.6, 0.6]'  # Sums to 1.2 > 1.0

        with pytest.raises(ValueError, match="sum to 1.0"):
            component.split_data()

    def test_invalid_chunk_size(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "chunk_size"
        component.chunk_size = 0

        with pytest.raises(ValueError, match="greater than 0"):
            component.split_data()

    def test_invalid_split_field(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "field_value"
        component.split_field = "nonexistent_field"

        with pytest.raises(ValueError, match="not found"):
            component.split_data()

    def test_insufficient_data_for_ratios(self, component):
        small_data = [Data(data={"id": 1})]
        component.data = small_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.4, 0.3, 0.3]'  # 3 splits for 1 record

        # Should handle gracefully, possibly with warning
        result = component.split_data()
        assert len(result.data) <= 3

    def test_single_record(self, component):
        single_data = [Data(data={"id": 1, "category": "A"})]
        component.data = single_data
        component.split_strategy = "ratio"
        component.split_ratios = '[1.0]'

        result = component.split_data()

        assert len(result.data) == 1
        assert len(result.data[0]["data"]) == 1
        assert result.data[0]["data"][0]["id"] == 1

    def test_zero_ratio_handling(self, component, sample_data):
        component.data = sample_data
        component.split_strategy = "ratio"
        component.split_ratios = '[0.8, 0.2, 0.0]'  # Third split gets 0%

        result = component.split_data()

        # Should have 3 splits, with third one empty
        assert len(result.data) == 3
        assert len(result.data[2]["data"]) == 0