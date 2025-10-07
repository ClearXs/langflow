import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    MessageTextInput,
    Output
)
from lfx.schema.data import Data


class FieldSelectorComponent(Component):
    display_name = i18n.t('components.data.field_selector.display_name')
    description = i18n.t('components.data.field_selector.description')
    icon = "filter"
    name = "FieldSelector"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.field_selector.data.display_name'),
            info=i18n.t('components.data.field_selector.data.info'),
            input_types=["Data"]
        ),

        # Selection mode
        DropdownInput(
            name="selection_mode",
            display_name=i18n.t('components.data.field_selector.selection_mode.display_name'),
            info=i18n.t('components.data.field_selector.selection_mode.info'),
            options=["include", "exclude", "regex_include", "regex_exclude", "conditional"],
            value="include",
            real_time_refresh=True,
        ),

        # Field lists
        MessageTextInput(
            name="include_fields",
            display_name=i18n.t('components.data.field_selector.include_fields.display_name'),
            info=i18n.t('components.data.field_selector.include_fields.info'),
            placeholder='["field1", "field2", "field3"]',
            show=True,
        ),

        MessageTextInput(
            name="exclude_fields",
            display_name=i18n.t('components.data.field_selector.exclude_fields.display_name'),
            info=i18n.t('components.data.field_selector.exclude_fields.info'),
            placeholder='["unwanted_field1", "unwanted_field2"]',
            show=False,
        ),

        # Regex patterns
        MessageTextInput(
            name="regex_pattern",
            display_name=i18n.t('components.data.field_selector.regex_pattern.display_name'),
            info=i18n.t('components.data.field_selector.regex_pattern.info'),
            placeholder=r'^(user_|account_)',
            show=False,
            advanced=True,
        ),

        # Conditional selection
        MessageTextInput(
            name="field_conditions",
            display_name=i18n.t('components.data.field_selector.field_conditions.display_name'),
            info=i18n.t('components.data.field_selector.field_conditions.info'),
            placeholder='{"has_data": true, "type": "string", "min_length": 3}',
            show=False,
            advanced=True,
        ),

        # Field renaming
        BoolInput(
            name="enable_renaming",
            display_name=i18n.t('components.data.field_selector.enable_renaming.display_name'),
            info=i18n.t('components.data.field_selector.enable_renaming.info'),
            value=False,
            advanced=True,
            real_time_refresh=True,
        ),

        MessageTextInput(
            name="field_mapping",
            display_name=i18n.t('components.data.field_selector.field_mapping.display_name'),
            info=i18n.t('components.data.field_selector.field_mapping.info'),
            placeholder='{"old_name": "new_name", "user_id": "id"}',
            show=False,
            advanced=True,
        ),

        # Field ordering
        BoolInput(
            name="preserve_order",
            display_name=i18n.t('components.data.field_selector.preserve_order.display_name'),
            info=i18n.t('components.data.field_selector.preserve_order.info'),
            value=True,
            advanced=True,
        ),

        MessageTextInput(
            name="field_order",
            display_name=i18n.t('components.data.field_selector.field_order.display_name'),
            info=i18n.t('components.data.field_selector.field_order.info'),
            placeholder='["id", "name", "email", "created_at"]',
            show=False,
            advanced=True,
        ),

        # Processing options
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t('components.data.field_selector.case_sensitive.display_name'),
            info=i18n.t('components.data.field_selector.case_sensitive.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="strict_mode",
            display_name=i18n.t('components.data.field_selector.strict_mode.display_name'),
            info=i18n.t('components.data.field_selector.strict_mode.info'),
            value=False,
            advanced=True,
        ),

        BoolInput(
            name="include_metadata",
            display_name=i18n.t('components.data.field_selector.include_metadata.display_name'),
            info=i18n.t('components.data.field_selector.include_metadata.info'),
            value=False,
            advanced=True,
        ),

        BoolInput(
            name="flatten_nested",
            display_name=i18n.t('components.data.field_selector.flatten_nested.display_name'),
            info=i18n.t('components.data.field_selector.flatten_nested.info'),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="selected_data",
            display_name=i18n.t('components.data.field_selector.outputs.selected_data.display_name'),
            method="select_fields"
        ),
        Output(
            name="selection_report",
            display_name=i18n.t('components.data.field_selector.outputs.selection_report.display_name'),
            method="get_selection_report"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selection_report = None
        self._selected_data = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on selection mode."""
        if field_name == "selection_mode":
            # Hide all mode-specific fields first
            for field in ["include_fields", "exclude_fields", "regex_pattern", "field_conditions"]:
                if field in build_config:
                    build_config[field]["show"] = False

            # Show relevant fields based on mode
            if field_value == "include":
                build_config["include_fields"]["show"] = True
            elif field_value == "exclude":
                build_config["exclude_fields"]["show"] = True
            elif field_value in ["regex_include", "regex_exclude"]:
                build_config["regex_pattern"]["show"] = True
            elif field_value == "conditional":
                build_config["field_conditions"]["show"] = True

        elif field_name == "enable_renaming":
            build_config["field_mapping"]["show"] = bool(field_value)

        elif field_name == "preserve_order":
            # Show field_order only if preserve_order is False
            build_config["field_order"]["show"] = not bool(field_value)

        return build_config

    def select_fields(self) -> list[Data]:
        """Main method to select and filter fields from data."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.field_selector.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.field_selector.errors.empty_data'))

            # Initialize selection report
            selection_report = {
                "summary": {
                    "total_records": len(data_list),
                    "processed_records": 0,
                    "original_field_count": 0,
                    "selected_field_count": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "selection_mode": self.selection_mode,
                },
                "field_analysis": {
                    "original_fields": set(),
                    "selected_fields": set(),
                    "excluded_fields": set(),
                    "renamed_fields": {},
                },
                "processing_details": [],
                "errors": []
            }

            # Analyze original fields
            for record in data_list:
                if isinstance(record, dict):
                    selection_report["field_analysis"]["original_fields"].update(record.keys())

            original_fields = list(selection_report["field_analysis"]["original_fields"])
            selection_report["summary"]["original_field_count"] = len(original_fields)

            # Determine selected fields based on mode
            selected_fields = self._determine_selected_fields(original_fields, data_list)
            selection_report["field_analysis"]["selected_fields"] = set(selected_fields)
            selection_report["field_analysis"]["excluded_fields"] = set(original_fields) - set(selected_fields)
            selection_report["summary"]["selected_field_count"] = len(selected_fields)

            # Get field mapping for renaming
            field_mapping = self._get_field_mapping()
            selection_report["field_analysis"]["renamed_fields"] = field_mapping

            # Process each record
            selected_data = []
            for record_idx, record in enumerate(data_list):
                try:
                    processed_record = self._process_record(
                        record, selected_fields, field_mapping, record_idx
                    )
                    selected_data.append(processed_record)
                    selection_report["summary"]["processed_records"] += 1

                except Exception as e:
                    selection_report["errors"].append({
                        "record_index": record_idx,
                        "error": str(e)
                    })
                    # Keep original record if processing fails in non-strict mode
                    if not self.strict_mode:
                        selected_data.append(record)

            # Add metadata if requested
            if self.include_metadata:
                metadata = self._generate_metadata(selection_report)
                for record in selected_data:
                    if isinstance(record, dict):
                        record["_field_selection_metadata"] = metadata

            # Generate processing details
            selection_report["processing_details"] = self._generate_processing_details(selection_report)

            # Store results
            self._selected_data = [Data(data=record) for record in selected_data]
            self._selection_report = Data(
                text=self._format_selection_report(selection_report),
                data=selection_report
            )

            # Update status
            fields_removed = len(original_fields) - len(selected_fields)
            self.status = f"Selected {len(selected_fields)} fields from {len(original_fields)}, removed {fields_removed} fields"

            return self._selected_data

        except Exception as e:
            error_message = i18n.t('components.data.field_selector.errors.selection_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_selection_report(self) -> Data:
        """Return the field selection report."""
        if self._selection_report is None:
            raise ValueError(i18n.t('components.data.field_selector.errors.no_selection_run'))
        return self._selection_report

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
                raise ValueError(i18n.t('components.data.field_selector.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _determine_selected_fields(self, original_fields: list, data_list: list) -> list:
        """Determine which fields to select based on the selection mode."""
        if self.selection_mode == "include":
            return self._select_include_fields(original_fields)

        elif self.selection_mode == "exclude":
            return self._select_exclude_fields(original_fields)

        elif self.selection_mode == "regex_include":
            return self._select_regex_include_fields(original_fields)

        elif self.selection_mode == "regex_exclude":
            return self._select_regex_exclude_fields(original_fields)

        elif self.selection_mode == "conditional":
            return self._select_conditional_fields(original_fields, data_list)

        else:
            raise ValueError(f"Unknown selection mode: {self.selection_mode}")

    def _select_include_fields(self, original_fields: list) -> list:
        """Select only specified fields to include."""
        try:
            include_fields = json.loads(self.include_fields) if isinstance(self.include_fields, str) else self.include_fields or []
        except json.JSONDecodeError:
            include_fields = []

        if not include_fields:
            return original_fields  # If no fields specified, include all

        selected = []
        for field in include_fields:
            if self.case_sensitive:
                if field in original_fields:
                    selected.append(field)
            else:
                # Case-insensitive matching
                for orig_field in original_fields:
                    if orig_field.lower() == field.lower():
                        selected.append(orig_field)
                        break

        return selected

    def _select_exclude_fields(self, original_fields: list) -> list:
        """Exclude specified fields."""
        try:
            exclude_fields = json.loads(self.exclude_fields) if isinstance(self.exclude_fields, str) else self.exclude_fields or []
        except json.JSONDecodeError:
            exclude_fields = []

        if not exclude_fields:
            return original_fields  # If no fields to exclude, include all

        selected = []
        for field in original_fields:
            should_exclude = False

            for exclude_field in exclude_fields:
                if self.case_sensitive:
                    if field == exclude_field:
                        should_exclude = True
                        break
                else:
                    if field.lower() == exclude_field.lower():
                        should_exclude = True
                        break

            if not should_exclude:
                selected.append(field)

        return selected

    def _select_regex_include_fields(self, original_fields: list) -> list:
        """Include fields matching regex pattern."""
        if not self.regex_pattern:
            return original_fields

        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            pattern = re.compile(self.regex_pattern, flags)

            selected = []
            for field in original_fields:
                if pattern.search(field):
                    selected.append(field)

            return selected

        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def _select_regex_exclude_fields(self, original_fields: list) -> list:
        """Exclude fields matching regex pattern."""
        if not self.regex_pattern:
            return original_fields

        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            pattern = re.compile(self.regex_pattern, flags)

            selected = []
            for field in original_fields:
                if not pattern.search(field):
                    selected.append(field)

            return selected

        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def _select_conditional_fields(self, original_fields: list, data_list: list) -> list:
        """Select fields based on conditional criteria."""
        try:
            conditions = json.loads(self.field_conditions) if isinstance(self.field_conditions, str) else self.field_conditions or {}
        except json.JSONDecodeError:
            conditions = {}

        if not conditions:
            return original_fields

        selected = []

        for field in original_fields:
            if self._field_meets_conditions(field, conditions, data_list):
                selected.append(field)

        return selected

    def _field_meets_conditions(self, field_name: str, conditions: dict, data_list: list) -> bool:
        """Check if a field meets the specified conditions."""
        # Analyze field across all records
        field_values = []
        non_null_values = []

        for record in data_list:
            if isinstance(record, dict) and field_name in record:
                value = record[field_name]
                field_values.append(value)
                if value is not None and value != "":
                    non_null_values.append(value)

        # Check conditions
        for condition, expected in conditions.items():
            if condition == "has_data":
                # Field must have non-null data
                has_data = len(non_null_values) > 0
                if has_data != expected:
                    return False

            elif condition == "min_non_null_ratio":
                # Minimum ratio of non-null values
                if field_values:
                    ratio = len(non_null_values) / len(field_values)
                    if ratio < expected:
                        return False

            elif condition == "type":
                # Field must be of specific type
                if non_null_values:
                    field_type = self._determine_field_type(non_null_values)
                    if field_type != expected:
                        return False

            elif condition == "min_length":
                # For string fields, minimum average length
                if non_null_values:
                    string_values = [str(v) for v in non_null_values]
                    avg_length = sum(len(s) for s in string_values) / len(string_values)
                    if avg_length < expected:
                        return False

            elif condition == "unique_values":
                # Minimum number of unique values
                unique_count = len(set(str(v) for v in non_null_values))
                if unique_count < expected:
                    return False

            elif condition == "max_unique_ratio":
                # Maximum ratio of unique values (to filter out mostly unique fields like IDs)
                if non_null_values:
                    unique_ratio = len(set(str(v) for v in non_null_values)) / len(non_null_values)
                    if unique_ratio > expected:
                        return False

        return True

    def _determine_field_type(self, values: list) -> str:
        """Determine the predominant type of field values."""
        type_counts = {"string": 0, "integer": 0, "float": 0, "boolean": 0, "other": 0}

        for value in values[:100]:  # Sample first 100 values for performance
            if isinstance(value, bool):
                type_counts["boolean"] += 1
            elif isinstance(value, int):
                type_counts["integer"] += 1
            elif isinstance(value, float):
                type_counts["float"] += 1
            elif isinstance(value, str):
                type_counts["string"] += 1
            else:
                type_counts["other"] += 1

        # Return the most common type
        return max(type_counts.items(), key=lambda x: x[1])[0]

    def _get_field_mapping(self) -> dict:
        """Get field mapping for renaming."""
        if not self.enable_renaming or not self.field_mapping:
            return {}

        try:
            return json.loads(self.field_mapping) if isinstance(self.field_mapping, str) else self.field_mapping or {}
        except json.JSONDecodeError:
            return {}

    def _process_record(self, record: dict, selected_fields: list, field_mapping: dict, record_idx: int) -> dict:
        """Process a single record to select and rename fields."""
        if not isinstance(record, dict):
            return record

        processed_record = {}

        # Handle nested flattening if requested
        if self.flatten_nested:
            record = self._flatten_nested_dict(record)

        # Determine field processing order
        if not self.preserve_order and self.field_order:
            try:
                field_order = json.loads(self.field_order) if isinstance(self.field_order, str) else self.field_order
                # Reorder selected_fields based on field_order
                ordered_fields = []
                for field in field_order:
                    if field in selected_fields:
                        ordered_fields.append(field)
                # Add any remaining fields not in order
                for field in selected_fields:
                    if field not in ordered_fields:
                        ordered_fields.append(field)
                selected_fields = ordered_fields
            except json.JSONDecodeError:
                pass

        # Select and process fields
        for field in selected_fields:
            if field in record:
                # Get the value
                value = record[field]

                # Determine output field name (rename if mapping exists)
                output_field = field_mapping.get(field, field)

                # Add to processed record
                processed_record[output_field] = value

        return processed_record

    def _flatten_nested_dict(self, data: dict, parent_key: str = '', sep: str = '_') -> dict:
        """Flatten nested dictionary structure."""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_nested_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))

        return dict(items)

    def _generate_metadata(self, report: dict) -> dict:
        """Generate metadata about field selection."""
        return {
            "selection_timestamp": report["summary"]["processing_timestamp"],
            "selection_mode": report["summary"]["selection_mode"],
            "original_field_count": report["summary"]["original_field_count"],
            "selected_field_count": report["summary"]["selected_field_count"],
            "excluded_fields": list(report["field_analysis"]["excluded_fields"]),
            "renamed_fields": report["field_analysis"]["renamed_fields"]
        }

    def _generate_processing_details(self, report: dict) -> dict:
        """Generate detailed processing information."""
        return {
            "field_reduction_rate": (
                (report["summary"]["original_field_count"] - report["summary"]["selected_field_count"]) /
                report["summary"]["original_field_count"] * 100
            ) if report["summary"]["original_field_count"] > 0 else 0,

            "selection_efficiency": (
                report["summary"]["processed_records"] /
                report["summary"]["total_records"] * 100
            ) if report["summary"]["total_records"] > 0 else 0,

            "field_mapping_applied": len(report["field_analysis"]["renamed_fields"]) > 0,
            "error_rate": (
                len(report["errors"]) /
                report["summary"]["total_records"] * 100
            ) if report["summary"]["total_records"] > 0 else 0
        }

    def _format_selection_report(self, report: dict) -> str:
        """Format the selection report into readable text."""
        report_lines = []
        summary = report["summary"]

        report_lines.append("=== FIELD SELECTION REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Selection Mode: {summary['selection_mode']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Processed Records: {summary['processed_records']}")
        report_lines.append(f"  Original Fields: {summary['original_field_count']}")
        report_lines.append(f"  Selected Fields: {summary['selected_field_count']}")

        fields_removed = summary['original_field_count'] - summary['selected_field_count']
        report_lines.append(f"  Fields Removed: {fields_removed}")

        if summary['original_field_count'] > 0:
            reduction_rate = (fields_removed / summary['original_field_count']) * 100
            report_lines.append(f"  Field Reduction Rate: {reduction_rate:.2f}%")

        # Field analysis
        field_analysis = report["field_analysis"]
        if field_analysis["selected_fields"]:
            report_lines.append("")
            report_lines.append("SELECTED FIELDS:")
            for field in sorted(field_analysis["selected_fields"]):
                # Check if field was renamed
                if field in field_analysis["renamed_fields"]:
                    new_name = field_analysis["renamed_fields"][field]
                    report_lines.append(f"  {field} → {new_name}")
                else:
                    report_lines.append(f"  {field}")

        if field_analysis["excluded_fields"]:
            report_lines.append("")
            report_lines.append("EXCLUDED FIELDS:")
            for field in sorted(field_analysis["excluded_fields"]):
                report_lines.append(f"  {field}")

        # Errors
        if report["errors"]:
            report_lines.append("")
            report_lines.append("ERRORS:")
            for error in report["errors"]:
                report_lines.append(f"  Record {error['record_index']}: {error['error']}")

        # Processing details
        if "processing_details" in report:
            details = report["processing_details"]
            report_lines.append("")
            report_lines.append("PROCESSING DETAILS:")
            report_lines.append(f"  Selection Efficiency: {details['selection_efficiency']:.2f}%")
            report_lines.append(f"  Field Mapping Applied: {details['field_mapping_applied']}")
            if details['error_rate'] > 0:
                report_lines.append(f"  Error Rate: {details['error_rate']:.2f}%")

        return "\n".join(report_lines)