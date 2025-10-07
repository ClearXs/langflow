import json
import pytest
from unittest.mock import Mock, patch
import math

from lfx.components.data.null_filler import NullFillerComponent
from lfx.schema.data import Data


class TestNullFillerComponent:
    """Test suite for NullFillerComponent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.component = NullFillerComponent()

        # Mock translation function to return key
        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            self.component.display_name = "Null Filler"
            self.component.description = "Test null filler"

    def test_component_initialization(self):
        """Test component initializes correctly."""
        assert self.component.display_name == "Null Filler"
        assert self.component.icon == "fill"
        assert self.component.name == "NullFiller"
        assert len(self.component.inputs) == 11
        assert len(self.component.outputs) == 3

    def test_parse_input_data_list_of_data_objects(self):
        """Test parsing list of Data objects."""
        data_objects = [
            Data(data={"id": 1, "name": "John", "age": None}),
            Data(data={"id": 2, "name": "", "age": 25})
        ]
        self.component.data = data_objects

        result = self.component._parse_input_data()

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "John", "age": None}
        assert result[1] == {"id": 2, "name": "", "age": 25}

    def test_parse_input_data_json_string(self):
        """Test parsing JSON string."""
        json_data = json.dumps([{"id": 1, "name": "John", "value": None}, {"id": 2, "name": "", "value": 42}])
        self.component.data = json_data

        result = self.component._parse_input_data()

        assert len(result) == 2
        assert result[0]["value"] is None
        assert result[1]["name"] == ""

    def test_is_null_value_basic(self):
        """Test basic null value detection."""
        self.component.treat_empty_string_as_null = True
        self.component.treat_whitespace_as_null = True

        assert self.component._is_null_value(None, []) is True
        assert self.component._is_null_value("", []) is True
        assert self.component._is_null_value("   ", []) is True
        assert self.component._is_null_value("valid", []) is False
        assert self.component._is_null_value(42, []) is False

    def test_is_null_value_custom_nulls(self):
        """Test custom null value detection."""
        custom_nulls = ["N/A", "NULL", "null", "-"]

        assert self.component._is_null_value("N/A", custom_nulls) is True
        assert self.component._is_null_value("NULL", custom_nulls) is True
        assert self.component._is_null_value("-", custom_nulls) is True
        assert self.component._is_null_value("valid", custom_nulls) is False

    def test_is_null_value_nan(self):
        """Test NaN detection."""
        assert self.component._is_null_value(float('nan'), []) is True
        assert self.component._is_null_value(3.14, []) is False

    def test_extract_numeric_values(self):
        """Test numeric value extraction from mixed data."""
        values = [1, 2.5, "3", "4.5", "not_a_number", None, 6]

        numeric_values = self.component._extract_numeric_values(values)

        assert len(numeric_values) == 5  # 1, 2.5, 3, 4.5, 6
        assert 1.0 in numeric_values
        assert 2.5 in numeric_values
        assert 3.0 in numeric_values
        assert 4.5 in numeric_values
        assert 6.0 in numeric_values

    def test_convert_to_appropriate_type(self):
        """Test type conversion functionality."""
        # Integer conversion
        assert self.component._convert_to_appropriate_type("42", "int") == 42
        assert self.component._convert_to_appropriate_type("3.0", "int") == 3

        # Float conversion
        assert self.component._convert_to_appropriate_type("3.14", "float") == 3.14
        assert self.component._convert_to_appropriate_type(42, "float") == 42.0

        # String conversion
        assert self.component._convert_to_appropriate_type(42, "str") == "42"

        # Boolean conversion
        assert self.component._convert_to_appropriate_type("true", "bool") is True
        assert self.component._convert_to_appropriate_type("false", "bool") is False
        assert self.component._convert_to_appropriate_type(1, "bool") is True

    def test_forward_fill(self):
        """Test forward fill strategy."""
        data_list = [
            {"id": 1, "name": "John", "score": 85},
            {"id": 2, "name": "Jane", "score": None},  # Should be filled with 85
            {"id": 3, "name": "Bob", "score": 92}
        ]

        result = self.component._forward_fill(data_list, 1, "score")
        assert result == 85

        # Test no previous value
        result = self.component._forward_fill(data_list, 0, "missing_field")
        assert result is None

    def test_backward_fill(self):
        """Test backward fill strategy."""
        data_list = [
            {"id": 1, "name": "John", "score": 85},
            {"id": 2, "name": "Jane", "score": None},  # Should be filled with 92
            {"id": 3, "name": "Bob", "score": 92}
        ]

        result = self.component._backward_fill(data_list, 1, "score")
        assert result == 92

        # Test no next value
        result = self.component._backward_fill(data_list, 2, "missing_field")
        assert result is None

    def test_interpolate_value(self):
        """Test interpolation strategy."""
        data_list = [
            {"id": 1, "value": 10},
            {"id": 2, "value": None},  # Should be interpolated to 15
            {"id": 3, "value": 20}
        ]

        result = self.component._interpolate_value(data_list, 1, "value")
        assert result == 15.0

        # Test non-numeric values
        data_list_str = [
            {"id": 1, "value": "not_number"},
            {"id": 2, "value": None},
            {"id": 3, "value": "also_not_number"}
        ]

        result = self.component._interpolate_value(data_list_str, 1, "value")
        assert result is None

    def test_get_fill_value_constant(self):
        """Test constant fill strategy."""
        strategy_config = {"strategy": "constant", "value": "default_value"}
        field_stats = {"data_type": "str", "non_null_values": ["a", "b", "c"]}

        result = self.component._get_fill_value(
            field_name="test_field",
            strategy="constant",
            strategy_config=strategy_config,
            field_stats=field_stats,
            data_list=[],
            record_idx=0,
            original_value=None
        )

        assert result == "default_value"

    def test_get_fill_value_mean(self):
        """Test mean fill strategy."""
        strategy_config = {"strategy": "mean"}
        field_stats = {"data_type": "float", "non_null_values": [10, 20, 30]}

        result = self.component._get_fill_value(
            field_name="test_field",
            strategy="mean",
            strategy_config=strategy_config,
            field_stats=field_stats,
            data_list=[],
            record_idx=0,
            original_value=None
        )

        assert result == 20.0

    def test_get_fill_value_median(self):
        """Test median fill strategy."""
        strategy_config = {"strategy": "median"}
        field_stats = {"data_type": "float", "non_null_values": [10, 15, 20, 25, 30]}

        result = self.component._get_fill_value(
            field_name="test_field",
            strategy="median",
            strategy_config=strategy_config,
            field_stats=field_stats,
            data_list=[],
            record_idx=0,
            original_value=None
        )

        assert result == 20.0

    def test_get_fill_value_mode(self):
        """Test mode fill strategy."""
        strategy_config = {"strategy": "mode"}
        field_stats = {"data_type": "str", "non_null_values": ["A", "B", "A", "C", "A"]}

        result = self.component._get_fill_value(
            field_name="test_field",
            strategy="mode",
            strategy_config=strategy_config,
            field_stats=field_stats,
            data_list=[],
            record_idx=0,
            original_value=None
        )

        assert result == "A"

    def test_validate_filled_data(self):
        """Test validation of filled data."""
        filled_data = [
            {"id": 1, "name": "John", "score": 85},
            {"id": 2, "name": "Jane", "score": 90},
            {"id": 3, "name": "", "score": 95}  # Empty string, should be detected if configured
        ]

        self.component.treat_empty_string_as_null = True
        results = self.component._validate_filled_data(filled_data)

        assert results["remaining_nulls"] == 1
        assert results["validation_passed"] is False
        assert results["field_validation"]["name"]["remaining_nulls"] == 1

    def test_fill_nulls_basic_constant_strategy(self):
        """Test basic null filling with constant strategy."""
        test_data = [
            Data(data={"id": 1, "name": "John", "score": None}),
            Data(data={"id": 2, "name": "", "score": 85}),
            Data(data={"id": 3, "name": "Bob", "score": 90})
        ]

        self.component.data = test_data
        self.component.default_strategy = "constant"
        self.component.default_fill_value = "Unknown"
        self.component.treat_empty_string_as_null = True

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        assert len(result) == 3
        assert result[0].data["name"] == "John"
        assert result[0].data["score"] == "Unknown"  # Filled
        assert result[1].data["name"] == "Unknown"  # Empty string filled
        assert result[1].data["score"] == 85

    def test_fill_nulls_mean_strategy(self):
        """Test null filling with mean strategy for numeric fields."""
        test_data = [
            Data(data={"id": 1, "score": 80}),
            Data(data={"id": 2, "score": None}),  # Should be filled with mean (85)
            Data(data={"id": 3, "score": 90})
        ]

        self.component.data = test_data
        self.component.default_strategy = "mean"

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        assert len(result) == 3
        assert result[1].data["score"] == 85.0  # Mean of 80 and 90

    def test_fill_nulls_field_specific_strategies(self):
        """Test field-specific fill strategies."""
        test_data = [
            Data(data={"id": 1, "name": "John", "age": 30, "score": 85}),
            Data(data={"id": 2, "name": None, "age": None, "score": None}),
        ]

        self.component.data = test_data
        self.component.use_field_strategies = True
        self.component.field_strategies = json.dumps({
            "name": {"strategy": "constant", "value": "Unknown"},
            "age": {"strategy": "mean"},
            "score": {"strategy": "forward_fill"}
        })

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        assert len(result) == 2
        assert result[1].data["name"] == "Unknown"  # Constant fill
        assert result[1].data["age"] == 30.0  # Mean fill
        assert result[1].data["score"] == 85  # Forward fill

    def test_fill_nulls_with_custom_null_values(self):
        """Test filling with custom null value definitions."""
        test_data = [
            Data(data={"id": 1, "status": "active"}),
            Data(data={"id": 2, "status": "N/A"}),  # Custom null value
            Data(data={"id": 3, "status": "NULL"}),  # Custom null value
        ]

        self.component.data = test_data
        self.component.default_strategy = "constant"
        self.component.default_fill_value = "unknown"
        self.component.custom_null_values = json.dumps(["N/A", "NULL", "null"])

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        assert len(result) == 3
        assert result[0].data["status"] == "active"
        assert result[1].data["status"] == "unknown"  # N/A filled
        assert result[2].data["status"] == "unknown"  # NULL filled

    def test_get_fill_report_without_fill(self):
        """Test getting fill report without running fill first."""
        with pytest.raises(ValueError):
            self.component.get_fill_report()

    def test_get_original_nulls_without_fill(self):
        """Test getting original nulls without running fill first."""
        with pytest.raises(ValueError):
            self.component.get_original_nulls()

    def test_update_build_config(self):
        """Test build config updates based on field changes."""
        build_config = {
            "default_fill_value": {"show": False},
            "field_strategies": {"show": False}
        }

        # Test default_strategy field
        result = self.component.update_build_config(build_config, "constant", "default_strategy")
        assert result["default_fill_value"]["show"] is True

        result = self.component.update_build_config(build_config, "mean", "default_strategy")
        assert result["default_fill_value"]["show"] is False

        # Test use_field_strategies field
        result = self.component.update_build_config(build_config, True, "use_field_strategies")
        assert result["field_strategies"]["show"] is True

        result = self.component.update_build_config(build_config, False, "use_field_strategies")
        assert result["field_strategies"]["show"] is False

    def test_fill_nulls_with_validation(self):
        """Test fill operation with post-fill validation enabled."""
        test_data = [
            Data(data={"id": 1, "name": "John", "score": 85}),
            Data(data={"id": 2, "name": None, "score": None}),
        ]

        self.component.data = test_data
        self.component.default_strategy = "constant"
        self.component.default_fill_value = "filled"
        self.component.validate_after_fill = True
        self.component.include_statistics = True

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        # Get the fill report to check validation results
        report = self.component.get_fill_report()

        assert len(result) == 2
        assert "validation" in report.data
        assert "statistics" in report.data

    def test_fill_nulls_interpolation_strategy(self):
        """Test interpolation strategy with numeric data."""
        test_data = [
            Data(data={"id": 1, "value": 10}),
            Data(data={"id": 2, "value": None}),  # Should be interpolated
            Data(data={"id": 3, "value": None}),  # Should be interpolated
            Data(data={"id": 4, "value": 30})
        ]

        self.component.data = test_data
        self.component.default_strategy = "interpolate"

        with patch('i18n.t', side_effect=lambda key, **kwargs: key.format(**kwargs) if kwargs else key):
            result = self.component.fill_nulls()

        assert len(result) == 4
        # Linear interpolation between 10 and 30
        assert abs(result[1].data["value"] - 16.67) < 0.1  # ~16.67
        assert abs(result[2].data["value"] - 23.33) < 0.1  # ~23.33

    def test_format_fill_report(self):
        """Test fill report formatting."""
        fill_report = {
            "summary": {
                "total_records": 5,
                "processed_records": 5,
                "total_nulls_found": 3,
                "total_nulls_filled": 2,
                "processing_timestamp": "2024-01-01T12:00:00",
                "default_strategy": "mean"
            },
            "field_analysis": {
                "score": {
                    "null_count": 2,
                    "null_percentage": 40.0,
                    "fill_strategy": "mean",
                    "data_type": "int"
                }
            },
            "errors": [],
            "statistics": {
                "fill_success_rate": 66.67,
                "data_quality_improvement": 66.67,
                "strategy_usage": {
                    "mean": {"count": 2, "success_count": 2}
                }
            }
        }

        report_text = self.component._format_fill_report(fill_report)

        assert "NULL FILL REPORT" in report_text
        assert "Total Records: 5" in report_text
        assert "Total Nulls Found: 3" in report_text
        assert "Total Nulls Filled: 2" in report_text
        assert "Fill Success Rate: 66.67%" in report_text
        assert "score:" in report_text