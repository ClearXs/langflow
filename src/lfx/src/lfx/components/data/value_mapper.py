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
    StrInput,
    Output
)
from lfx.schema.data import Data


class ValueMapperComponent(Component):
    display_name = i18n.t('components.data.value_mapper.display_name')
    description = i18n.t('components.data.value_mapper.description')
    icon = "shuffle"
    name = "ValueMapper"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.value_mapper.data.display_name'),
            info=i18n.t('components.data.value_mapper.data.info'),
            input_types=["Data"]
        ),

        # Mapping mode
        DropdownInput(
            name="mapping_mode",
            display_name=i18n.t('components.data.value_mapper.mapping_mode.display_name'),
            info=i18n.t('components.data.value_mapper.mapping_mode.info'),
            options=["simple", "conditional", "calculated", "lookup_table", "regex_pattern"],
            value="simple",
            real_time_refresh=True,
        ),

        # Target fields
        MessageTextInput(
            name="target_fields",
            display_name=i18n.t('components.data.value_mapper.target_fields.display_name'),
            info=i18n.t('components.data.value_mapper.target_fields.info'),
            placeholder='["status", "category", "priority"]',
            advanced=True,
        ),

        # Simple mapping
        MessageTextInput(
            name="value_mappings",
            display_name=i18n.t('components.data.value_mapper.value_mappings.display_name'),
            info=i18n.t('components.data.value_mapper.value_mappings.info'),
            placeholder='{"active": "ACTIVE", "inactive": "INACTIVE", "pending": "PENDING"}',
            show=True,
        ),

        # Conditional mapping
        MessageTextInput(
            name="conditional_mappings",
            display_name=i18n.t('components.data.value_mapper.conditional_mappings.display_name'),
            info=i18n.t('components.data.value_mapper.conditional_mappings.info'),
            placeholder='[{"condition": "score > 80", "value": "excellent"}, {"condition": "score > 60", "value": "good"}]',
            show=False,
            advanced=True,
        ),

        # Calculated mapping
        MessageTextInput(
            name="calculation_rules",
            display_name=i18n.t('components.data.value_mapper.calculation_rules.display_name'),
            info=i18n.t('components.data.value_mapper.calculation_rules.info'),
            placeholder='{"full_name": "first_name + \' \' + last_name", "age_group": "\'adult\' if age >= 18 else \'minor\'"}',
            show=False,
            advanced=True,
        ),

        # Lookup table
        MessageTextInput(
            name="lookup_table",
            display_name=i18n.t('components.data.value_mapper.lookup_table.display_name'),
            info=i18n.t('components.data.value_mapper.lookup_table.info'),
            placeholder='{"lookup_field": "country_code", "lookup_data": [{"code": "US", "name": "United States"}]}',
            show=False,
            advanced=True,
        ),

        # Regex pattern mapping
        MessageTextInput(
            name="regex_mappings",
            display_name=i18n.t('components.data.value_mapper.regex_mappings.display_name'),
            info=i18n.t('components.data.value_mapper.regex_mappings.info'),
            placeholder='[{"pattern": "^\\\\d{3}-\\\\d{2}-\\\\d{4}$", "replacement": "SSN Format"}, {"pattern": "^\\\\w+@\\\\w+", "replacement": "Email"}]',
            show=False,
            advanced=True,
        ),

        # Processing options
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t('components.data.value_mapper.case_sensitive.display_name'),
            info=i18n.t('components.data.value_mapper.case_sensitive.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="create_new_fields",
            display_name=i18n.t('components.data.value_mapper.create_new_fields.display_name'),
            info=i18n.t('components.data.value_mapper.create_new_fields.info'),
            value=False,
            advanced=True,
        ),

        StrInput(
            name="new_field_suffix",
            display_name=i18n.t('components.data.value_mapper.new_field_suffix.display_name'),
            info=i18n.t('components.data.value_mapper.new_field_suffix.info'),
            value="_mapped",
            show=False,
            advanced=True,
        ),

        StrInput(
            name="default_value",
            display_name=i18n.t('components.data.value_mapper.default_value.display_name'),
            info=i18n.t('components.data.value_mapper.default_value.info'),
            value="",
            advanced=True,
        ),

        BoolInput(
            name="preserve_original",
            display_name=i18n.t('components.data.value_mapper.preserve_original.display_name'),
            info=i18n.t('components.data.value_mapper.preserve_original.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="strict_mode",
            display_name=i18n.t('components.data.value_mapper.strict_mode.display_name'),
            info=i18n.t('components.data.value_mapper.strict_mode.info'),
            value=False,
            advanced=True,
        ),

        BoolInput(
            name="include_mapping_stats",
            display_name=i18n.t('components.data.value_mapper.include_mapping_stats.display_name'),
            info=i18n.t('components.data.value_mapper.include_mapping_stats.info'),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="mapped_data",
            display_name=i18n.t('components.data.value_mapper.outputs.mapped_data.display_name'),
            method="map_values"
        ),
        Output(
            name="mapping_report",
            display_name=i18n.t('components.data.value_mapper.outputs.mapping_report.display_name'),
            method="get_mapping_report"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mapping_report = None
        self._mapped_data = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on mapping mode."""
        if field_name == "mapping_mode":
            # Hide all mode-specific fields first
            for field in ["value_mappings", "conditional_mappings", "calculation_rules", "lookup_table", "regex_mappings"]:
                if field in build_config:
                    build_config[field]["show"] = False

            # Show relevant fields based on mode
            if field_value == "simple":
                build_config["value_mappings"]["show"] = True
            elif field_value == "conditional":
                build_config["conditional_mappings"]["show"] = True
            elif field_value == "calculated":
                build_config["calculation_rules"]["show"] = True
            elif field_value == "lookup_table":
                build_config["lookup_table"]["show"] = True
            elif field_value == "regex_pattern":
                build_config["regex_mappings"]["show"] = True

        elif field_name == "create_new_fields":
            build_config["new_field_suffix"]["show"] = bool(field_value)

        return build_config

    def map_values(self) -> list[Data]:
        """Main method to perform value mapping."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.value_mapper.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.value_mapper.errors.empty_data'))

            # Initialize mapping report
            mapping_report = {
                "summary": {
                    "total_records": len(data_list),
                    "processed_records": 0,
                    "total_mappings": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "mapping_mode": self.mapping_mode,
                },
                "field_statistics": {},
                "mapping_details": [],
                "unmapped_values": {},
                "errors": []
            }

            # Get target fields
            target_fields = self._get_target_fields()

            # Process each record
            mapped_data = []
            for record_idx, record in enumerate(data_list):
                try:
                    processed_record, record_stats = self._process_record(
                        record, record_idx, target_fields
                    )
                    mapped_data.append(processed_record)

                    # Update statistics
                    mapping_report["summary"]["processed_records"] += 1
                    mapping_report["summary"]["total_mappings"] += record_stats["total_mappings"]

                    if record_stats["mappings"]:
                        mapping_report["mapping_details"].append({
                            "record_index": record_idx,
                            "mappings": record_stats["mappings"]
                        })

                    # Update field statistics
                    for field, field_stats in record_stats["field_stats"].items():
                        if field not in mapping_report["field_statistics"]:
                            mapping_report["field_statistics"][field] = {
                                "total_values": 0,
                                "mapped_values": 0,
                                "unique_mappings": set(),
                                "unmapped_values": set()
                            }

                        mapping_report["field_statistics"][field]["total_values"] += 1
                        if field_stats["mapped"]:
                            mapping_report["field_statistics"][field]["mapped_values"] += 1
                            original = field_stats.get("original_value")
                            mapped = field_stats.get("mapped_value")
                            if original is not None and mapped is not None:
                                mapping_report["field_statistics"][field]["unique_mappings"].add(f"{original} → {mapped}")
                        else:
                            unmapped_value = field_stats.get("original_value")
                            if unmapped_value is not None:
                                mapping_report["field_statistics"][field]["unmapped_values"].add(str(unmapped_value))

                except Exception as e:
                    mapping_report["errors"].append({
                        "record_index": record_idx,
                        "error": str(e)
                    })
                    # Keep original record if processing fails and not in strict mode
                    if not self.strict_mode:
                        mapped_data.append(record)

            # Convert sets to lists for JSON serialization
            for field_stats in mapping_report["field_statistics"].values():
                field_stats["unique_mappings"] = list(field_stats["unique_mappings"])
                field_stats["unmapped_values"] = list(field_stats["unmapped_values"])

            # Collect unmapped values summary
            for field, stats in mapping_report["field_statistics"].items():
                if stats["unmapped_values"]:
                    mapping_report["unmapped_values"][field] = stats["unmapped_values"]

            # Generate overall statistics
            if self.include_mapping_stats:
                mapping_report["statistics"] = self._generate_mapping_statistics(mapping_report)

            # Store results
            self._mapped_data = [Data(data=record) for record in mapped_data]
            self._mapping_report = Data(
                text=self._format_mapping_report(mapping_report),
                data=mapping_report
            )

            # Update status
            self.status = f"Processed {mapping_report['summary']['processed_records']} records, made {mapping_report['summary']['total_mappings']} value mappings"

            return self._mapped_data

        except Exception as e:
            error_message = i18n.t('components.data.value_mapper.errors.mapping_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_mapping_report(self) -> Data:
        """Return the mapping report."""
        if self._mapping_report is None:
            raise ValueError(i18n.t('components.data.value_mapper.errors.no_mapping_run'))
        return self._mapping_report

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
                raise ValueError(i18n.t('components.data.value_mapper.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _get_target_fields(self) -> list:
        """Get the list of target fields to process."""
        if not self.target_fields:
            return None  # Process all fields

        try:
            return json.loads(self.target_fields) if isinstance(self.target_fields, str) else self.target_fields
        except json.JSONDecodeError:
            return []

    def _process_record(self, record: dict, record_idx: int, target_fields: list = None) -> tuple[dict, dict]:
        """Process a single record for value mapping."""
        processed_record = record.copy()
        record_stats = {
            "total_mappings": 0,
            "mappings": [],
            "field_stats": {}
        }

        # Determine fields to process
        fields_to_process = target_fields if target_fields else list(record.keys())

        for field_name in fields_to_process:
            if field_name not in record:
                continue

            original_value = record[field_name]

            # Apply mapping based on mode
            try:
                mapped_value, mapping_applied = self._apply_mapping(
                    original_value, field_name, record, record_idx
                )

                # Determine output field name
                if self.create_new_fields and mapping_applied:
                    output_field = f"{field_name}{self.new_field_suffix}"
                else:
                    output_field = field_name

                # Update record
                if mapping_applied:
                    if self.preserve_original and self.create_new_fields:
                        # Keep original and add new field
                        processed_record[output_field] = mapped_value
                    else:
                        # Replace original value
                        processed_record[field_name] = mapped_value

                    record_stats["total_mappings"] += 1
                    record_stats["mappings"].append({
                        "field": field_name,
                        "original_value": original_value,
                        "mapped_value": mapped_value,
                        "output_field": output_field
                    })

                # Record field statistics
                record_stats["field_stats"][field_name] = {
                    "original_value": original_value,
                    "mapped_value": mapped_value if mapping_applied else original_value,
                    "mapped": mapping_applied,
                    "output_field": output_field
                }

            except Exception as e:
                # Log field-level error but continue processing
                record_stats["field_stats"][field_name] = {
                    "original_value": original_value,
                    "mapped_value": original_value,
                    "mapped": False,
                    "error": str(e)
                }

        return processed_record, record_stats

    def _apply_mapping(self, value: Any, field_name: str, record: dict, record_idx: int) -> tuple[Any, bool]:
        """Apply mapping based on the selected mode."""
        if self.mapping_mode == "simple":
            return self._apply_simple_mapping(value)

        elif self.mapping_mode == "conditional":
            return self._apply_conditional_mapping(value, record)

        elif self.mapping_mode == "calculated":
            return self._apply_calculated_mapping(value, field_name, record)

        elif self.mapping_mode == "lookup_table":
            return self._apply_lookup_mapping(value, field_name, record)

        elif self.mapping_mode == "regex_pattern":
            return self._apply_regex_mapping(value)

        else:
            raise ValueError(f"Unknown mapping mode: {self.mapping_mode}")

    def _apply_simple_mapping(self, value: Any) -> tuple[Any, bool]:
        """Apply simple value mapping."""
        try:
            mappings = json.loads(self.value_mappings) if isinstance(self.value_mappings, str) else self.value_mappings or {}
        except json.JSONDecodeError:
            mappings = {}

        if not mappings:
            return value, False

        # Convert value to string for comparison
        str_value = str(value)

        # Check for direct mapping
        for map_key, map_value in mappings.items():
            if self.case_sensitive:
                if str_value == str(map_key):
                    return map_value, True
            else:
                if str_value.lower() == str(map_key).lower():
                    return map_value, True

        # No mapping found, return default or original
        if self.default_value:
            return self.default_value, True
        return value, False

    def _apply_conditional_mapping(self, value: Any, record: dict) -> tuple[Any, bool]:
        """Apply conditional mapping based on record context."""
        try:
            conditions = json.loads(self.conditional_mappings) if isinstance(self.conditional_mappings, str) else self.conditional_mappings or []
        except json.JSONDecodeError:
            conditions = []

        if not conditions:
            return value, False

        # Create evaluation context
        eval_context = record.copy()
        eval_context["value"] = value

        for condition_rule in conditions:
            if not isinstance(condition_rule, dict):
                continue

            condition = condition_rule.get("condition", "")
            result_value = condition_rule.get("value", value)

            try:
                # Simple condition evaluation (limited for security)
                if self._evaluate_condition(condition, eval_context):
                    return result_value, True
            except Exception:
                # Skip invalid conditions
                continue

        # No condition matched
        if self.default_value:
            return self.default_value, True
        return value, False

    def _apply_calculated_mapping(self, value: Any, field_name: str, record: dict) -> tuple[Any, bool]:
        """Apply calculated mapping using expressions."""
        try:
            calculations = json.loads(self.calculation_rules) if isinstance(self.calculation_rules, str) else self.calculation_rules or {}
        except json.JSONDecodeError:
            calculations = {}

        if field_name not in calculations:
            return value, False

        expression = calculations[field_name]
        eval_context = record.copy()
        eval_context["value"] = value

        try:
            # Simple expression evaluation (limited for security)
            result = self._evaluate_expression(expression, eval_context)
            return result, True
        except Exception:
            if self.default_value:
                return self.default_value, True
            return value, False

    def _apply_lookup_mapping(self, value: Any, field_name: str, record: dict) -> tuple[Any, bool]:
        """Apply lookup table mapping."""
        try:
            lookup_config = json.loads(self.lookup_table) if isinstance(self.lookup_table, str) else self.lookup_table or {}
        except json.JSONDecodeError:
            lookup_config = {}

        if not lookup_config:
            return value, False

        lookup_field = lookup_config.get("lookup_field")
        lookup_data = lookup_config.get("lookup_data", [])
        result_field = lookup_config.get("result_field", "name")

        if not lookup_field or not lookup_data:
            return value, False

        # Find matching record in lookup table
        for lookup_record in lookup_data:
            if not isinstance(lookup_record, dict):
                continue

            lookup_value = lookup_record.get(lookup_field)
            if lookup_value is None:
                continue

            # Check for match
            if self.case_sensitive:
                if str(value) == str(lookup_value):
                    result = lookup_record.get(result_field, lookup_record)
                    return result, True
            else:
                if str(value).lower() == str(lookup_value).lower():
                    result = lookup_record.get(result_field, lookup_record)
                    return result, True

        # No match found
        if self.default_value:
            return self.default_value, True
        return value, False

    def _apply_regex_mapping(self, value: Any) -> tuple[Any, bool]:
        """Apply regex pattern mapping."""
        try:
            regex_mappings = json.loads(self.regex_mappings) if isinstance(self.regex_mappings, str) else self.regex_mappings or []
        except json.JSONDecodeError:
            regex_mappings = []

        if not regex_mappings:
            return value, False

        str_value = str(value)

        for mapping_rule in regex_mappings:
            if not isinstance(mapping_rule, dict):
                continue

            pattern = mapping_rule.get("pattern", "")
            replacement = mapping_rule.get("replacement", "")

            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                if re.search(pattern, str_value, flags):
                    # Apply replacement
                    if "groups" in mapping_rule and mapping_rule["groups"]:
                        # Use regex groups for substitution
                        result = re.sub(pattern, replacement, str_value, flags=flags)
                    else:
                        # Simple replacement
                        result = replacement
                    return result, True
            except re.error:
                # Skip invalid regex patterns
                continue

        # No pattern matched
        if self.default_value:
            return self.default_value, True
        return value, False

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Safely evaluate a simple condition."""
        # This is a simplified condition evaluator for security
        # In production, you might want to use a more robust expression evaluator

        # Replace variables with actual values
        for key, value in context.items():
            if isinstance(value, str):
                condition = condition.replace(key, f"'{value}'")
            else:
                condition = condition.replace(key, str(value))

        # Only allow simple comparison operations
        allowed_operations = ["==", "!=", ">=", "<=", ">", "<", "in", "not in"]

        for op in allowed_operations:
            if op in condition:
                try:
                    # Very basic evaluation - in production use a proper expression evaluator
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()

                        # Convert to appropriate types
                        try:
                            left_val = eval(left) if left.startswith(("'", '"')) or left.replace('.', '').isdigit() else left
                            right_val = eval(right) if right.startswith(("'", '"')) or right.replace('.', '').isdigit() else right
                        except:
                            return False

                        # Perform comparison
                        if op == "==":
                            return left_val == right_val
                        elif op == "!=":
                            return left_val != right_val
                        elif op == ">":
                            return float(left_val) > float(right_val)
                        elif op == "<":
                            return float(left_val) < float(right_val)
                        elif op == ">=":
                            return float(left_val) >= float(right_val)
                        elif op == "<=":
                            return float(left_val) <= float(right_val)
                        elif op == "in":
                            return left_val in right_val
                        elif op == "not in":
                            return left_val not in right_val

                except:
                    return False

        return False

    def _evaluate_expression(self, expression: str, context: dict) -> Any:
        """Safely evaluate a simple expression."""
        # This is a simplified expression evaluator
        # Replace variables with values
        for key, value in context.items():
            if isinstance(value, str):
                expression = expression.replace(key, f"'{value}'")
            else:
                expression = expression.replace(key, str(value))

        # Only allow simple operations and built-in functions
        if any(dangerous in expression for dangerous in ["import", "__", "eval", "exec", "open", "file"]):
            raise ValueError("Dangerous operation in expression")

        try:
            # Very limited evaluation - consider using a proper expression library
            return eval(expression)
        except:
            raise ValueError("Invalid expression")

    def _generate_mapping_statistics(self, report: dict) -> dict:
        """Generate comprehensive mapping statistics."""
        stats = {
            "mapping_rate": 0.0,
            "most_active_field": None,
            "mapping_coverage": {},
            "effectiveness_score": 0.0
        }

        summary = report["summary"]
        total_records = summary["total_records"]
        total_mappings = summary["total_mappings"]

        if total_records > 0:
            stats["mapping_rate"] = (total_mappings / total_records) * 100

        # Find most active field
        field_stats = report["field_statistics"]
        if field_stats:
            most_active = max(field_stats.items(), key=lambda x: x[1]["mapped_values"])
            stats["most_active_field"] = {
                "field_name": most_active[0],
                "mapped_values": most_active[1]["mapped_values"],
                "total_values": most_active[1]["total_values"]
            }

        # Calculate mapping coverage per field
        for field, stats_data in field_stats.items():
            if stats_data["total_values"] > 0:
                coverage = (stats_data["mapped_values"] / stats_data["total_values"]) * 100
                stats["mapping_coverage"][field] = coverage

        # Calculate effectiveness score
        if field_stats:
            total_coverage = sum(stats["mapping_coverage"].values())
            stats["effectiveness_score"] = total_coverage / len(field_stats) if field_stats else 0

        return stats

    def _format_mapping_report(self, report: dict) -> str:
        """Format the mapping report into readable text."""
        report_lines = []
        summary = report["summary"]

        report_lines.append("=== VALUE MAPPING REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Mapping Mode: {summary['mapping_mode']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Processed Records: {summary['processed_records']}")
        report_lines.append(f"  Total Mappings: {summary['total_mappings']}")

        if summary['processed_records'] > 0:
            avg_mappings = summary['total_mappings'] / summary['processed_records']
            report_lines.append(f"  Average Mappings per Record: {avg_mappings:.2f}")

        # Field statistics
        if report["field_statistics"]:
            report_lines.append("")
            report_lines.append("FIELD STATISTICS:")
            for field, stats in report["field_statistics"].items():
                report_lines.append(f"  {field}:")
                report_lines.append(f"    Values Mapped: {stats['mapped_values']}/{stats['total_values']}")
                if stats['total_values'] > 0:
                    mapping_rate = (stats['mapped_values'] / stats['total_values']) * 100
                    report_lines.append(f"    Mapping Rate: {mapping_rate:.2f}%")

                # Show unique mappings
                if stats['unique_mappings']:
                    report_lines.append(f"    Unique Mappings: {len(stats['unique_mappings'])}")
                    for mapping in stats['unique_mappings'][:5]:  # Show first 5
                        report_lines.append(f"      {mapping}")
                    if len(stats['unique_mappings']) > 5:
                        report_lines.append(f"      ... and {len(stats['unique_mappings']) - 5} more")

        # Unmapped values
        if report["unmapped_values"]:
            report_lines.append("")
            report_lines.append("UNMAPPED VALUES:")
            for field, unmapped in report["unmapped_values"].items():
                report_lines.append(f"  {field}: {', '.join(unmapped[:10])}")
                if len(unmapped) > 10:
                    report_lines.append(f"    ... and {len(unmapped) - 10} more")

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
            report_lines.append(f"  Overall Mapping Rate: {stats['mapping_rate']:.2f}%")
            report_lines.append(f"  Effectiveness Score: {stats['effectiveness_score']:.2f}%")

            if stats["most_active_field"]:
                most_active = stats["most_active_field"]
                report_lines.append(f"  Most Active Field: {most_active['field_name']} ({most_active['mapped_values']} mappings)")

        return "\n".join(report_lines)