import json
import statistics
from datetime import datetime
from typing import Any, Dict, List, Union
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    MessageTextInput,
    StrInput,
    Output
)
from lfx.schema.data import Data


class NullFillerComponent(Component):
    display_name = i18n.t('components.data.null_filler.display_name')
    description = i18n.t('components.data.null_filler.description')
    icon = "fill"
    name = "NullFiller"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.null_filler.data.display_name'),
            info=i18n.t('components.data.null_filler.data.info'),
            input_types=["Data"]
        ),

        # Global fill strategy
        DropdownInput(
            name="default_strategy",
            display_name=i18n.t('components.data.null_filler.default_strategy.display_name'),
            info=i18n.t('components.data.null_filler.default_strategy.info'),
            options=["constant", "mean", "median", "mode", "forward_fill", "backward_fill", "interpolate", "remove"],
            value="constant",
            real_time_refresh=True,
        ),

        # Default fill value for constant strategy
        StrInput(
            name="default_fill_value",
            display_name=i18n.t('components.data.null_filler.default_fill_value.display_name'),
            info=i18n.t('components.data.null_filler.default_fill_value.info'),
            value="",
            show=True,
        ),

        # Field-specific strategies
        BoolInput(
            name="use_field_strategies",
            display_name=i18n.t('components.data.null_filler.use_field_strategies.display_name'),
            info=i18n.t('components.data.null_filler.use_field_strategies.info'),
            value=False,
            advanced=True,
            real_time_refresh=True,
        ),

        MessageTextInput(
            name="field_strategies",
            display_name=i18n.t('components.data.null_filler.field_strategies.display_name'),
            info=i18n.t('components.data.null_filler.field_strategies.info'),
            placeholder='{"age": {"strategy": "mean"}, "name": {"strategy": "constant", "value": "Unknown"}}',
            show=False,
            advanced=True,
        ),

        # Null detection options
        BoolInput(
            name="treat_empty_string_as_null",
            display_name=i18n.t('components.data.null_filler.treat_empty_string_as_null.display_name'),
            info=i18n.t('components.data.null_filler.treat_empty_string_as_null.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="treat_whitespace_as_null",
            display_name=i18n.t('components.data.null_filler.treat_whitespace_as_null.display_name'),
            info=i18n.t('components.data.null_filler.treat_whitespace_as_null.info'),
            value=False,
            advanced=True,
        ),

        MessageTextInput(
            name="custom_null_values",
            display_name=i18n.t('components.data.null_filler.custom_null_values.display_name'),
            info=i18n.t('components.data.null_filler.custom_null_values.info'),
            placeholder='["N/A", "NULL", "null", "-", "undefined"]',
            advanced=True,
        ),

        # Output options
        BoolInput(
            name="preserve_original_order",
            display_name=i18n.t('components.data.null_filler.preserve_original_order.display_name'),
            info=i18n.t('components.data.null_filler.preserve_original_order.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="include_statistics",
            display_name=i18n.t('components.data.null_filler.include_statistics.display_name'),
            info=i18n.t('components.data.null_filler.include_statistics.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="validate_after_fill",
            display_name=i18n.t('components.data.null_filler.validate_after_fill.display_name'),
            info=i18n.t('components.data.null_filler.validate_after_fill.info'),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="filled_data",
            display_name=i18n.t('components.data.null_filler.outputs.filled_data.display_name'),
            method="fill_nulls"
        ),
        Output(
            name="fill_report",
            display_name=i18n.t('components.data.null_filler.outputs.fill_report.display_name'),
            method="get_fill_report"
        ),
        Output(
            name="original_nulls",
            display_name=i18n.t('components.data.null_filler.outputs.original_nulls.display_name'),
            method="get_original_nulls"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fill_report = None
        self._original_nulls = None
        self._filled_data = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on strategy selection."""
        if field_name == "default_strategy":
            build_config["default_fill_value"]["show"] = (field_value == "constant")
        elif field_name == "use_field_strategies":
            build_config["field_strategies"]["show"] = bool(field_value)
        return build_config

    def fill_nulls(self) -> list[Data]:
        """Main method to fill null values in the data."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.null_filler.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.null_filler.errors.empty_data'))

            # Initialize fill report
            fill_report = {
                "summary": {
                    "total_records": len(data_list),
                    "processed_records": 0,
                    "total_nulls_found": 0,
                    "total_nulls_filled": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "default_strategy": self.default_strategy,
                },
                "field_analysis": {},
                "fill_operations": [],
                "errors": [],
                "statistics": {}
            }

            # Get field strategies
            field_strategies = self._get_field_strategies()

            # Get custom null values
            custom_nulls = self._get_custom_null_values()

            # Analyze data and identify nulls
            original_nulls = []
            field_stats = {}

            # First pass: identify all nulls and collect field statistics
            for record_idx, record in enumerate(data_list):
                record_nulls = {}
                for field_name, value in record.items():
                    if field_name not in field_stats:
                        field_stats[field_name] = {
                            "total_count": 0,
                            "null_count": 0,
                            "non_null_values": [],
                            "data_type": None
                        }

                    field_stats[field_name]["total_count"] += 1

                    if self._is_null_value(value, custom_nulls):
                        field_stats[field_name]["null_count"] += 1
                        record_nulls[field_name] = value
                        fill_report["summary"]["total_nulls_found"] += 1
                    else:
                        field_stats[field_name]["non_null_values"].append(value)
                        if field_stats[field_name]["data_type"] is None:
                            field_stats[field_name]["data_type"] = type(value).__name__

                if record_nulls:
                    original_nulls.append({
                        "record_index": record_idx,
                        "null_fields": record_nulls
                    })

            # Calculate statistics for each field
            for field_name, stats in field_stats.items():
                field_analysis = {
                    "total_count": stats["total_count"],
                    "null_count": stats["null_count"],
                    "null_percentage": (stats["null_count"] / stats["total_count"]) * 100,
                    "data_type": stats["data_type"],
                    "fill_strategy": field_strategies.get(field_name, {}).get("strategy", self.default_strategy)
                }

                # Calculate statistical values for numeric fields
                if stats["non_null_values"]:
                    numeric_values = self._extract_numeric_values(stats["non_null_values"])
                    if numeric_values:
                        field_analysis["mean"] = statistics.mean(numeric_values)
                        field_analysis["median"] = statistics.median(numeric_values)
                        try:
                            field_analysis["mode"] = statistics.mode(stats["non_null_values"])
                        except statistics.StatisticsError:
                            field_analysis["mode"] = stats["non_null_values"][0] if stats["non_null_values"] else None

                fill_report["field_analysis"][field_name] = field_analysis

            # Second pass: fill null values
            filled_data = []
            for record_idx, record in enumerate(data_list):
                filled_record = record.copy()
                record_operations = []

                for field_name, value in record.items():
                    if self._is_null_value(value, custom_nulls):
                        strategy_config = field_strategies.get(field_name, {"strategy": self.default_strategy})
                        strategy = strategy_config["strategy"]

                        try:
                            fill_value = self._get_fill_value(
                                field_name=field_name,
                                strategy=strategy,
                                strategy_config=strategy_config,
                                field_stats=field_stats[field_name],
                                data_list=data_list,
                                record_idx=record_idx,
                                original_value=value
                            )

                            if fill_value is not None:
                                filled_record[field_name] = fill_value
                                record_operations.append({
                                    "field": field_name,
                                    "original_value": value,
                                    "fill_value": fill_value,
                                    "strategy": strategy,
                                    "success": True
                                })
                                fill_report["summary"]["total_nulls_filled"] += 1
                            else:
                                record_operations.append({
                                    "field": field_name,
                                    "original_value": value,
                                    "fill_value": None,
                                    "strategy": strategy,
                                    "success": False,
                                    "error": "Could not determine fill value"
                                })

                        except Exception as e:
                            record_operations.append({
                                "field": field_name,
                                "original_value": value,
                                "fill_value": None,
                                "strategy": strategy,
                                "success": False,
                                "error": str(e)
                            })
                            fill_report["errors"].append({
                                "record_index": record_idx,
                                "field": field_name,
                                "error": str(e),
                                "strategy": strategy
                            })

                if record_operations:
                    fill_report["fill_operations"].append({
                        "record_index": record_idx,
                        "operations": record_operations
                    })

                filled_data.append(filled_record)
                fill_report["summary"]["processed_records"] += 1

            # Validation after filling
            if self.validate_after_fill:
                validation_results = self._validate_filled_data(filled_data)
                fill_report["validation"] = validation_results

            # Generate final statistics
            if self.include_statistics:
                fill_report["statistics"] = self._generate_fill_statistics(fill_report)

            # Store results
            self._filled_data = [Data(data=record) for record in filled_data]
            self._fill_report = Data(
                text=self._format_fill_report(fill_report),
                data=fill_report
            )
            self._original_nulls = [Data(data=null_info) for null_info in original_nulls]

            self.status = f"Filled {fill_report['summary']['total_nulls_filled']}/{fill_report['summary']['total_nulls_found']} null values in {len(filled_data)} records"

            return self._filled_data

        except Exception as e:
            error_message = i18n.t('components.data.null_filler.errors.fill_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_fill_report(self) -> Data:
        """Return the fill operation report."""
        if self._fill_report is None:
            raise ValueError(i18n.t('components.data.null_filler.errors.no_fill_run'))
        return self._fill_report

    def get_original_nulls(self) -> list[Data]:
        """Return the original null values that were found."""
        if self._original_nulls is None:
            raise ValueError(i18n.t('components.data.null_filler.errors.no_fill_run'))
        return self._original_nulls

    def _parse_input_data(self) -> list[dict]:
        """Parse input data from various formats."""
        if isinstance(self.data, list):
            return [item.data if hasattr(item, 'data') else item for item in self.data]
        elif hasattr(self.data, 'data'):
            data_content = self.data.data
            return data_content if isinstance(data_content, list) else [data_content]
        elif isinstance(self.data, str):
            try:
                parsed = json.loads(self.data)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                raise ValueError(i18n.t('components.data.null_filler.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _get_field_strategies(self) -> dict:
        """Parse field-specific strategies from configuration."""
        if not self.use_field_strategies or not self.field_strategies:
            return {}

        try:
            return json.loads(self.field_strategies) if isinstance(self.field_strategies, str) else self.field_strategies
        except json.JSONDecodeError:
            return {}

    def _get_custom_null_values(self) -> list:
        """Parse custom null values from configuration."""
        if not self.custom_null_values:
            return []

        try:
            return json.loads(self.custom_null_values) if isinstance(self.custom_null_values, str) else self.custom_null_values
        except json.JSONDecodeError:
            return []

    def _is_null_value(self, value: Any, custom_nulls: list) -> bool:
        """Check if a value should be considered null."""
        # Standard null checks
        if value is None:
            return True

        # Empty string check
        if self.treat_empty_string_as_null and value == "":
            return True

        # Whitespace check
        if self.treat_whitespace_as_null and isinstance(value, str) and value.strip() == "":
            return True

        # Custom null values
        if custom_nulls and value in custom_nulls:
            return True

        # NaN check for numeric values
        if isinstance(value, float):
            try:
                import math
                return math.isnan(value)
            except (TypeError, ValueError):
                pass

        return False

    def _extract_numeric_values(self, values: list) -> list:
        """Extract numeric values from a list, converting strings if possible."""
        numeric_values = []
        for value in values:
            if isinstance(value, (int, float)):
                numeric_values.append(float(value))
            elif isinstance(value, str):
                try:
                    numeric_values.append(float(value))
                except (ValueError, TypeError):
                    continue
        return numeric_values

    def _get_fill_value(self, field_name: str, strategy: str, strategy_config: dict,
                       field_stats: dict, data_list: list, record_idx: int, original_value: Any) -> Any:
        """Get the fill value based on the specified strategy."""

        if strategy == "constant":
            fill_value = strategy_config.get("value", self.default_fill_value)
            return self._convert_to_appropriate_type(fill_value, field_stats.get("data_type"))

        elif strategy == "mean":
            numeric_values = self._extract_numeric_values(field_stats["non_null_values"])
            if numeric_values:
                mean_value = statistics.mean(numeric_values)
                return self._convert_to_appropriate_type(mean_value, field_stats.get("data_type"))
            return None

        elif strategy == "median":
            numeric_values = self._extract_numeric_values(field_stats["non_null_values"])
            if numeric_values:
                median_value = statistics.median(numeric_values)
                return self._convert_to_appropriate_type(median_value, field_stats.get("data_type"))
            return None

        elif strategy == "mode":
            if field_stats["non_null_values"]:
                try:
                    return statistics.mode(field_stats["non_null_values"])
                except statistics.StatisticsError:
                    return field_stats["non_null_values"][0]
            return None

        elif strategy == "forward_fill":
            return self._forward_fill(data_list, record_idx, field_name)

        elif strategy == "backward_fill":
            return self._backward_fill(data_list, record_idx, field_name)

        elif strategy == "interpolate":
            return self._interpolate_value(data_list, record_idx, field_name)

        elif strategy == "remove":
            return None  # This will be handled by removing the record

        else:
            raise ValueError(f"Unknown fill strategy: {strategy}")

    def _convert_to_appropriate_type(self, value: Any, target_type: str) -> Any:
        """Convert a value to the appropriate data type."""
        if target_type is None or value is None:
            return value

        try:
            if target_type == "int":
                return int(float(value))  # Convert through float to handle strings like "3.0"
            elif target_type == "float":
                return float(value)
            elif target_type == "str":
                return str(value)
            elif target_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                return value
        except (ValueError, TypeError):
            return value

    def _forward_fill(self, data_list: list, record_idx: int, field_name: str) -> Any:
        """Fill with the previous non-null value."""
        for i in range(record_idx - 1, -1, -1):
            if field_name in data_list[i]:
                value = data_list[i][field_name]
                if not self._is_null_value(value, self._get_custom_null_values()):
                    return value
        return None

    def _backward_fill(self, data_list: list, record_idx: int, field_name: str) -> Any:
        """Fill with the next non-null value."""
        for i in range(record_idx + 1, len(data_list)):
            if field_name in data_list[i]:
                value = data_list[i][field_name]
                if not self._is_null_value(value, self._get_custom_null_values()):
                    return value
        return None

    def _interpolate_value(self, data_list: list, record_idx: int, field_name: str) -> Any:
        """Interpolate value using linear interpolation."""
        # Find previous and next non-null numeric values
        prev_value = None
        prev_idx = None
        next_value = None
        next_idx = None

        # Find previous value
        for i in range(record_idx - 1, -1, -1):
            if field_name in data_list[i]:
                value = data_list[i][field_name]
                if not self._is_null_value(value, self._get_custom_null_values()):
                    try:
                        prev_value = float(value)
                        prev_idx = i
                        break
                    except (ValueError, TypeError):
                        continue

        # Find next value
        for i in range(record_idx + 1, len(data_list)):
            if field_name in data_list[i]:
                value = data_list[i][field_name]
                if not self._is_null_value(value, self._get_custom_null_values()):
                    try:
                        next_value = float(value)
                        next_idx = i
                        break
                    except (ValueError, TypeError):
                        continue

        # Perform linear interpolation
        if prev_value is not None and next_value is not None and prev_idx is not None and next_idx is not None:
            ratio = (record_idx - prev_idx) / (next_idx - prev_idx)
            interpolated = prev_value + ratio * (next_value - prev_value)
            return interpolated
        elif prev_value is not None:
            return prev_value
        elif next_value is not None:
            return next_value
        else:
            return None

    def _validate_filled_data(self, filled_data: list) -> dict:
        """Validate the filled data to ensure no nulls remain."""
        validation_results = {
            "remaining_nulls": 0,
            "validation_passed": True,
            "field_validation": {}
        }

        custom_nulls = self._get_custom_null_values()

        for record in filled_data:
            for field_name, value in record.items():
                if field_name not in validation_results["field_validation"]:
                    validation_results["field_validation"][field_name] = {
                        "remaining_nulls": 0,
                        "total_checked": 0
                    }

                validation_results["field_validation"][field_name]["total_checked"] += 1

                if self._is_null_value(value, custom_nulls):
                    validation_results["remaining_nulls"] += 1
                    validation_results["field_validation"][field_name]["remaining_nulls"] += 1
                    validation_results["validation_passed"] = False

        return validation_results

    def _generate_fill_statistics(self, fill_report: dict) -> dict:
        """Generate comprehensive statistics about the fill operation."""
        stats = {
            "fill_success_rate": 0.0,
            "strategy_usage": {},
            "field_fill_rates": {},
            "data_quality_improvement": 0.0
        }

        total_nulls = fill_report["summary"]["total_nulls_found"]
        filled_nulls = fill_report["summary"]["total_nulls_filled"]

        if total_nulls > 0:
            stats["fill_success_rate"] = (filled_nulls / total_nulls) * 100

        # Strategy usage statistics
        for operation_batch in fill_report["fill_operations"]:
            for operation in operation_batch["operations"]:
                strategy = operation["strategy"]
                if strategy not in stats["strategy_usage"]:
                    stats["strategy_usage"][strategy] = {"count": 0, "success_count": 0}

                stats["strategy_usage"][strategy]["count"] += 1
                if operation["success"]:
                    stats["strategy_usage"][strategy]["success_count"] += 1

        # Field-specific fill rates
        for field_name, analysis in fill_report["field_analysis"].items():
            if analysis["null_count"] > 0:
                filled_count = sum(
                    1 for batch in fill_report["fill_operations"]
                    for op in batch["operations"]
                    if op["field"] == field_name and op["success"]
                )
                stats["field_fill_rates"][field_name] = (filled_count / analysis["null_count"]) * 100

        # Overall data quality improvement
        if total_nulls > 0:
            stats["data_quality_improvement"] = (filled_nulls / total_nulls) * 100

        return stats

    def _format_fill_report(self, fill_report: dict) -> str:
        """Format the fill report into a readable text format."""
        report_lines = []
        summary = fill_report["summary"]

        report_lines.append("=== NULL FILL REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Default Strategy: {summary['default_strategy']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Processed Records: {summary['processed_records']}")
        report_lines.append(f"  Total Nulls Found: {summary['total_nulls_found']}")
        report_lines.append(f"  Total Nulls Filled: {summary['total_nulls_filled']}")

        if summary['total_nulls_found'] > 0:
            fill_rate = (summary['total_nulls_filled'] / summary['total_nulls_found']) * 100
            report_lines.append(f"  Fill Success Rate: {fill_rate:.2f}%")

        # Field analysis
        report_lines.append("")
        report_lines.append("FIELD ANALYSIS:")
        for field_name, analysis in fill_report["field_analysis"].items():
            if analysis["null_count"] > 0:
                report_lines.append(f"  {field_name}:")
                report_lines.append(f"    Null Count: {analysis['null_count']}")
                report_lines.append(f"    Null Percentage: {analysis['null_percentage']:.2f}%")
                report_lines.append(f"    Fill Strategy: {analysis['fill_strategy']}")
                report_lines.append(f"    Data Type: {analysis['data_type']}")

        # Errors
        if fill_report["errors"]:
            report_lines.append("")
            report_lines.append("ERRORS:")
            for error in fill_report["errors"]:
                report_lines.append(f"  Record {error['record_index']}, Field {error['field']}: {error['error']}")

        # Statistics
        if "statistics" in fill_report:
            stats = fill_report["statistics"]
            report_lines.append("")
            report_lines.append("STATISTICS:")
            report_lines.append(f"  Overall Fill Success Rate: {stats['fill_success_rate']:.2f}%")
            report_lines.append(f"  Data Quality Improvement: {stats['data_quality_improvement']:.2f}%")

            if stats["strategy_usage"]:
                report_lines.append("  Strategy Usage:")
                for strategy, usage in stats["strategy_usage"].items():
                    success_rate = (usage["success_count"] / usage["count"]) * 100 if usage["count"] > 0 else 0
                    report_lines.append(f"    {strategy}: {usage['count']} uses ({success_rate:.1f}% success)")

        return "\n".join(report_lines)