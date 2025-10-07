import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union, Pattern
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    MessageTextInput,
    IntInput,
    Output
)
from lfx.schema.data import Data


class StringReplacerComponent(Component):
    display_name = i18n.t('components.data.string_replacer.display_name')
    description = i18n.t('components.data.string_replacer.description')
    icon = "replace"
    name = "StringReplacer"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.string_replacer.data.display_name'),
            info=i18n.t('components.data.string_replacer.data.info'),
            input_types=["Data"]
        ),

        # Replacement mode
        DropdownInput(
            name="replacement_mode",
            display_name=i18n.t('components.data.string_replacer.replacement_mode.display_name'),
            info=i18n.t('components.data.string_replacer.replacement_mode.info'),
            options=["simple", "regex", "bulk", "template"],
            value="simple",
            real_time_refresh=True,
        ),

        # Simple replacement
        MessageTextInput(
            name="find_text",
            display_name=i18n.t('components.data.string_replacer.find_text.display_name'),
            info=i18n.t('components.data.string_replacer.find_text.info'),
            value="",
            show=True,
        ),

        MessageTextInput(
            name="replace_text",
            display_name=i18n.t('components.data.string_replacer.replace_text.display_name'),
            info=i18n.t('components.data.string_replacer.replace_text.info'),
            value="",
            show=True,
        ),

        # Regex pattern
        MessageTextInput(
            name="regex_pattern",
            display_name=i18n.t('components.data.string_replacer.regex_pattern.display_name'),
            info=i18n.t('components.data.string_replacer.regex_pattern.info'),
            placeholder=r'\d{3}-\d{3}-\d{4}',
            show=False,
            advanced=True,
        ),

        MessageTextInput(
            name="regex_replacement",
            display_name=i18n.t('components.data.string_replacer.regex_replacement.display_name'),
            info=i18n.t('components.data.string_replacer.regex_replacement.info'),
            placeholder=r'(\1) \2-\3',
            show=False,
            advanced=True,
        ),

        # Bulk replacements
        MessageTextInput(
            name="bulk_replacements",
            display_name=i18n.t('components.data.string_replacer.bulk_replacements.display_name'),
            info=i18n.t('components.data.string_replacer.bulk_replacements.info'),
            placeholder='{"old1": "new1", "old2": "new2", "pattern3": {"replace": "new3", "regex": true}}',
            show=False,
            advanced=True,
        ),

        # Template replacement
        MessageTextInput(
            name="template_pattern",
            display_name=i18n.t('components.data.string_replacer.template_pattern.display_name'),
            info=i18n.t('components.data.string_replacer.template_pattern.info'),
            placeholder='Hello {name}, your score is {score}',
            show=False,
            advanced=True,
        ),

        # Field selection
        MessageTextInput(
            name="target_fields",
            display_name=i18n.t('components.data.string_replacer.target_fields.display_name'),
            info=i18n.t('components.data.string_replacer.target_fields.info'),
            placeholder='["field1", "field2"]',
            advanced=True,
        ),

        # Options
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t('components.data.string_replacer.case_sensitive.display_name'),
            info=i18n.t('components.data.string_replacer.case_sensitive.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="whole_word_only",
            display_name=i18n.t('components.data.string_replacer.whole_word_only.display_name'),
            info=i18n.t('components.data.string_replacer.whole_word_only.info'),
            value=False,
            advanced=True,
        ),

        IntInput(
            name="max_replacements",
            display_name=i18n.t('components.data.string_replacer.max_replacements.display_name'),
            info=i18n.t('components.data.string_replacer.max_replacements.info'),
            value=0,
            range_spec={"min": 0, "max": 10000},
            advanced=True,
        ),

        # Processing options
        BoolInput(
            name="create_backup_fields",
            display_name=i18n.t('components.data.string_replacer.create_backup_fields.display_name'),
            info=i18n.t('components.data.string_replacer.create_backup_fields.info'),
            value=False,
            advanced=True,
        ),

        BoolInput(
            name="include_replacement_stats",
            display_name=i18n.t('components.data.string_replacer.include_replacement_stats.display_name'),
            info=i18n.t('components.data.string_replacer.include_replacement_stats.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="skip_non_string_fields",
            display_name=i18n.t('components.data.string_replacer.skip_non_string_fields.display_name'),
            info=i18n.t('components.data.string_replacer.skip_non_string_fields.info'),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="replaced_data",
            display_name=i18n.t('components.data.string_replacer.outputs.replaced_data.display_name'),
            method="replace_strings"
        ),
        Output(
            name="replacement_report",
            display_name=i18n.t('components.data.string_replacer.outputs.replacement_report.display_name'),
            method="get_replacement_report"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._replacement_report = None
        self._replaced_data = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on replacement mode."""
        if field_name == "replacement_mode":
            # Hide all mode-specific fields first
            for field in ["find_text", "replace_text", "regex_pattern", "regex_replacement", "bulk_replacements", "template_pattern"]:
                if field in build_config:
                    build_config[field]["show"] = False

            # Show relevant fields based on mode
            if field_value == "simple":
                build_config["find_text"]["show"] = True
                build_config["replace_text"]["show"] = True
            elif field_value == "regex":
                build_config["regex_pattern"]["show"] = True
                build_config["regex_replacement"]["show"] = True
            elif field_value == "bulk":
                build_config["bulk_replacements"]["show"] = True
            elif field_value == "template":
                build_config["template_pattern"]["show"] = True

        return build_config

    def replace_strings(self) -> list[Data]:
        """Main method to perform string replacements."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.string_replacer.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.string_replacer.errors.empty_data'))

            # Initialize replacement report
            replacement_report = {
                "summary": {
                    "total_records": len(data_list),
                    "processed_records": 0,
                    "total_replacements": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "replacement_mode": self.replacement_mode,
                },
                "field_statistics": {},
                "replacement_details": [],
                "errors": []
            }

            # Get target fields
            target_fields = self._get_target_fields()

            # Process each record
            replaced_data = []
            for record_idx, record in enumerate(data_list):
                try:
                    processed_record, record_stats = self._process_record(
                        record, record_idx, target_fields
                    )
                    replaced_data.append(processed_record)

                    # Update statistics
                    replacement_report["summary"]["processed_records"] += 1
                    replacement_report["summary"]["total_replacements"] += record_stats["total_replacements"]

                    if record_stats["replacements"]:
                        replacement_report["replacement_details"].append({
                            "record_index": record_idx,
                            "replacements": record_stats["replacements"]
                        })

                    # Update field statistics
                    for field, field_stats in record_stats["field_stats"].items():
                        if field not in replacement_report["field_statistics"]:
                            replacement_report["field_statistics"][field] = {
                                "total_records": 0,
                                "records_modified": 0,
                                "total_replacements": 0
                            }

                        replacement_report["field_statistics"][field]["total_records"] += 1
                        if field_stats["replacements"] > 0:
                            replacement_report["field_statistics"][field]["records_modified"] += 1
                            replacement_report["field_statistics"][field]["total_replacements"] += field_stats["replacements"]

                except Exception as e:
                    replacement_report["errors"].append({
                        "record_index": record_idx,
                        "error": str(e)
                    })
                    # Keep original record if processing fails
                    replaced_data.append(record)

            # Generate overall statistics
            if self.include_replacement_stats:
                replacement_report["statistics"] = self._generate_replacement_statistics(replacement_report)

            # Store results
            self._replaced_data = [Data(data=record) for record in replaced_data]
            self._replacement_report = Data(
                text=self._format_replacement_report(replacement_report),
                data=replacement_report
            )

            # Update status
            self.status = f"Processed {replacement_report['summary']['processed_records']} records, made {replacement_report['summary']['total_replacements']} replacements"

            return self._replaced_data

        except Exception as e:
            error_message = i18n.t('components.data.string_replacer.errors.replacement_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_replacement_report(self) -> Data:
        """Return the replacement report."""
        if self._replacement_report is None:
            raise ValueError(i18n.t('components.data.string_replacer.errors.no_replacement_run'))
        return self._replacement_report

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
                raise ValueError(i18n.t('components.data.string_replacer.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _get_target_fields(self) -> list:
        """Get the list of target fields to process."""
        if not self.target_fields:
            return None  # Process all string fields

        try:
            return json.loads(self.target_fields) if isinstance(self.target_fields, str) else self.target_fields
        except json.JSONDecodeError:
            return []

    def _process_record(self, record: dict, record_idx: int, target_fields: list = None) -> tuple[dict, dict]:
        """Process a single record for string replacements."""
        processed_record = record.copy()
        record_stats = {
            "total_replacements": 0,
            "replacements": [],
            "field_stats": {}
        }

        # Create backup fields if requested
        if self.create_backup_fields:
            for field_name, value in record.items():
                if isinstance(value, str) and (target_fields is None or field_name in target_fields):
                    processed_record[f"{field_name}_backup"] = value

        # Determine fields to process
        fields_to_process = target_fields if target_fields else list(record.keys())

        for field_name in fields_to_process:
            if field_name not in record:
                continue

            value = record[field_name]

            # Skip non-string fields if configured
            if not isinstance(value, str) and self.skip_non_string_fields:
                continue

            # Convert to string if not already
            if not isinstance(value, str):
                value = str(value)

            # Apply replacements based on mode
            try:
                new_value, field_replacements = self._apply_replacements(value, field_name)

                if new_value != value:
                    processed_record[field_name] = new_value
                    record_stats["total_replacements"] += len(field_replacements)
                    record_stats["replacements"].extend(field_replacements)

                record_stats["field_stats"][field_name] = {
                    "original_value": value,
                    "new_value": new_value,
                    "replacements": len(field_replacements)
                }

            except Exception as e:
                # Log field-level error but continue processing
                record_stats["field_stats"][field_name] = {
                    "original_value": value,
                    "new_value": value,
                    "replacements": 0,
                    "error": str(e)
                }

        return processed_record, record_stats

    def _apply_replacements(self, text: str, field_name: str) -> tuple[str, list]:
        """Apply replacements based on the selected mode."""
        replacements = []

        if self.replacement_mode == "simple":
            text, replacements = self._apply_simple_replacement(text)

        elif self.replacement_mode == "regex":
            text, replacements = self._apply_regex_replacement(text)

        elif self.replacement_mode == "bulk":
            text, replacements = self._apply_bulk_replacements(text)

        elif self.replacement_mode == "template":
            text, replacements = self._apply_template_replacement(text, field_name)

        else:
            raise ValueError(f"Unknown replacement mode: {self.replacement_mode}")

        return text, replacements

    def _apply_simple_replacement(self, text: str) -> tuple[str, list]:
        """Apply simple find and replace."""
        if not self.find_text:
            return text, []

        replacements = []
        find_text = self.find_text
        replace_text = self.replace_text or ""

        # Apply case sensitivity
        if not self.case_sensitive:
            # Use regex for case-insensitive replacement
            pattern = re.escape(find_text)
            if self.whole_word_only:
                pattern = r'\b' + pattern + r'\b'

            flags = re.IGNORECASE
            compiled_pattern = re.compile(pattern, flags)

            # Count matches before replacement
            matches = list(compiled_pattern.finditer(text))

            # Apply max replacements limit
            if self.max_replacements > 0:
                matches = matches[:self.max_replacements]

            # Perform replacement
            if matches:
                new_text = compiled_pattern.sub(replace_text, text, count=self.max_replacements if self.max_replacements > 0 else 0)
                for match in matches:
                    replacements.append({
                        "position": match.start(),
                        "original": match.group(),
                        "replacement": replace_text,
                        "type": "simple"
                    })
                return new_text, replacements
        else:
            # Case-sensitive replacement
            if self.whole_word_only:
                pattern = r'\b' + re.escape(find_text) + r'\b'
                compiled_pattern = re.compile(pattern)
                matches = list(compiled_pattern.finditer(text))

                if self.max_replacements > 0:
                    matches = matches[:self.max_replacements]

                if matches:
                    new_text = compiled_pattern.sub(replace_text, text, count=self.max_replacements if self.max_replacements > 0 else 0)
                    for match in matches:
                        replacements.append({
                            "position": match.start(),
                            "original": match.group(),
                            "replacement": replace_text,
                            "type": "simple_word_boundary"
                        })
                    return new_text, replacements
            else:
                # Simple string replacement
                count = self.max_replacements if self.max_replacements > 0 else -1
                new_text = text.replace(find_text, replace_text, count)

                if new_text != text:
                    # Count actual replacements made
                    if count == -1:
                        replacement_count = text.count(find_text)
                    else:
                        replacement_count = min(text.count(find_text), count)

                    # Record replacements
                    start_pos = 0
                    for _ in range(replacement_count):
                        pos = text.find(find_text, start_pos)
                        if pos != -1:
                            replacements.append({
                                "position": pos,
                                "original": find_text,
                                "replacement": replace_text,
                                "type": "simple"
                            })
                            start_pos = pos + len(find_text)

                    return new_text, replacements

        return text, []

    def _apply_regex_replacement(self, text: str) -> tuple[str, list]:
        """Apply regex pattern replacement."""
        if not self.regex_pattern:
            return text, []

        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            pattern = re.compile(self.regex_pattern, flags)
            replacement = self.regex_replacement or ""

            matches = list(pattern.finditer(text))

            # Apply max replacements limit
            if self.max_replacements > 0:
                matches = matches[:self.max_replacements]

            if matches:
                count = self.max_replacements if self.max_replacements > 0 else 0
                new_text = pattern.sub(replacement, text, count=count)

                replacements = []
                for match in matches:
                    replacements.append({
                        "position": match.start(),
                        "original": match.group(),
                        "replacement": replacement,
                        "type": "regex",
                        "pattern": self.regex_pattern
                    })

                return new_text, replacements

        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        return text, []

    def _apply_bulk_replacements(self, text: str) -> tuple[str, list]:
        """Apply multiple replacements from bulk configuration."""
        if not self.bulk_replacements:
            return text, []

        try:
            bulk_config = json.loads(self.bulk_replacements) if isinstance(self.bulk_replacements, str) else self.bulk_replacements
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for bulk replacements")

        replacements = []
        new_text = text

        for find_pattern, replace_config in bulk_config.items():
            if isinstance(replace_config, str):
                # Simple string replacement
                replace_value = replace_config
                is_regex = False
            elif isinstance(replace_config, dict):
                # Advanced replacement configuration
                replace_value = replace_config.get("replace", "")
                is_regex = replace_config.get("regex", False)
            else:
                continue

            if is_regex:
                # Apply regex replacement
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    pattern = re.compile(find_pattern, flags)
                    matches = list(pattern.finditer(new_text))

                    if matches:
                        count = self.max_replacements if self.max_replacements > 0 else 0
                        temp_text = pattern.sub(replace_value, new_text, count=count)

                        if temp_text != new_text:
                            for match in matches:
                                replacements.append({
                                    "position": match.start(),
                                    "original": match.group(),
                                    "replacement": replace_value,
                                    "type": "bulk_regex",
                                    "pattern": find_pattern
                                })
                            new_text = temp_text

                except re.error:
                    # Skip invalid regex patterns
                    continue
            else:
                # Simple string replacement
                if self.case_sensitive:
                    temp_text = new_text.replace(find_pattern, replace_value)
                else:
                    # Case-insensitive replacement using regex
                    pattern = re.compile(re.escape(find_pattern), re.IGNORECASE)
                    temp_text = pattern.sub(replace_value, new_text)

                if temp_text != new_text:
                    # Count replacements made
                    pattern_for_count = find_pattern if self.case_sensitive else find_pattern.lower()
                    text_for_count = new_text if self.case_sensitive else new_text.lower()
                    replacement_count = text_for_count.count(pattern_for_count)

                    for _ in range(replacement_count):
                        replacements.append({
                            "original": find_pattern,
                            "replacement": replace_value,
                            "type": "bulk_simple"
                        })
                    new_text = temp_text

        return new_text, replacements

    def _apply_template_replacement(self, text: str, field_name: str) -> tuple[str, list]:
        """Apply template-based replacement."""
        if not self.template_pattern:
            return text, []

        # This is a placeholder implementation
        # In a real scenario, you might want to use a template engine
        # or implement more sophisticated template replacement logic

        replacements = []
        template = self.template_pattern

        # Simple template variable replacement
        # Look for {variable_name} patterns
        import re
        variable_pattern = re.compile(r'\{(\w+)\}')
        variables = variable_pattern.findall(template)

        if variables:
            new_text = template
            for var in variables:
                # Replace with field value if available
                # This is a simplified implementation
                if var == field_name:
                    replacement_value = text
                    new_text = new_text.replace(f'{{{var}}}', replacement_value)
                    replacements.append({
                        "original": f'{{{var}}}',
                        "replacement": replacement_value,
                        "type": "template",
                        "variable": var
                    })

            if new_text != template:
                return new_text, replacements

        return text, []

    def _generate_replacement_statistics(self, report: dict) -> dict:
        """Generate comprehensive replacement statistics."""
        stats = {
            "replacement_rate": 0.0,
            "average_replacements_per_record": 0.0,
            "most_active_field": None,
            "replacement_efficiency": 0.0,
            "mode_effectiveness": {}
        }

        summary = report["summary"]
        total_records = summary["total_records"]
        processed_records = summary["processed_records"]
        total_replacements = summary["total_replacements"]

        if processed_records > 0:
            stats["replacement_rate"] = (processed_records / total_records) * 100
            stats["average_replacements_per_record"] = total_replacements / processed_records

        # Find most active field
        field_stats = report["field_statistics"]
        if field_stats:
            most_active = max(field_stats.items(), key=lambda x: x[1]["total_replacements"])
            stats["most_active_field"] = {
                "field_name": most_active[0],
                "total_replacements": most_active[1]["total_replacements"],
                "records_modified": most_active[1]["records_modified"]
            }

        # Calculate efficiency (replacements made vs records processed)
        if processed_records > 0:
            records_with_replacements = len([detail for detail in report["replacement_details"] if detail["replacements"]])
            stats["replacement_efficiency"] = (records_with_replacements / processed_records) * 100

        # Mode effectiveness
        stats["mode_effectiveness"] = {
            "mode_used": summary["replacement_mode"],
            "total_operations": total_replacements,
            "success_rate": (processed_records - len(report["errors"])) / total_records * 100 if total_records > 0 else 0
        }

        return stats

    def _format_replacement_report(self, report: dict) -> str:
        """Format the replacement report into readable text."""
        report_lines = []
        summary = report["summary"]

        report_lines.append("=== STRING REPLACEMENT REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Replacement Mode: {summary['replacement_mode']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Processed Records: {summary['processed_records']}")
        report_lines.append(f"  Total Replacements: {summary['total_replacements']}")

        if summary['processed_records'] > 0:
            avg_replacements = summary['total_replacements'] / summary['processed_records']
            report_lines.append(f"  Average Replacements per Record: {avg_replacements:.2f}")

        # Field statistics
        if report["field_statistics"]:
            report_lines.append("")
            report_lines.append("FIELD STATISTICS:")
            for field, stats in report["field_statistics"].items():
                report_lines.append(f"  {field}:")
                report_lines.append(f"    Records Modified: {stats['records_modified']}/{stats['total_records']}")
                report_lines.append(f"    Total Replacements: {stats['total_replacements']}")
                if stats['total_records'] > 0:
                    modification_rate = (stats['records_modified'] / stats['total_records']) * 100
                    report_lines.append(f"    Modification Rate: {modification_rate:.2f}%")

        # Errors
        if report["errors"]:
            report_lines.append("")
            report_lines.append("ERRORS:")
            for error in report["errors"]:
                report_lines.append(f"  Record {error['record_index']}: {error['error']}")

        # Statistics
        if "statistics" in report:
            stats = report["statistics"]
            report_lines.append("")
            report_lines.append("STATISTICS:")
            report_lines.append(f"  Replacement Rate: {stats['replacement_rate']:.2f}%")
            report_lines.append(f"  Replacement Efficiency: {stats['replacement_efficiency']:.2f}%")

            if stats["most_active_field"]:
                most_active = stats["most_active_field"]
                report_lines.append(f"  Most Active Field: {most_active['field_name']} ({most_active['total_replacements']} replacements)")

        return "\n".join(report_lines)