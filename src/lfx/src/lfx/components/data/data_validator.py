import json
import re
from datetime import datetime
from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    FloatInput,
    IntInput,
    MessageTextInput,
    StrInput,
    Output
)
from lfx.schema.data import Data


class DataValidatorComponent(Component):
    display_name = i18n.t('components.data.data_validator.display_name')
    description = i18n.t('components.data.data_validator.description')
    icon = "check-circle"
    name = "DataValidator"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.data_validator.data.display_name'),
            info=i18n.t('components.data.data_validator.data.info'),
            input_types=["Data"]
        ),

        # Validation mode
        DropdownInput(
            name="validation_mode",
            display_name=i18n.t('components.data.data_validator.validation_mode.display_name'),
            info=i18n.t('components.data.data_validator.validation_mode.info'),
            options=["strict", "tolerant", "report_only"],
            value="tolerant",
            real_time_refresh=True,
        ),

        # Validation rules
        BoolInput(
            name="check_null_values",
            display_name=i18n.t('components.data.data_validator.check_null_values.display_name'),
            info=i18n.t('components.data.data_validator.check_null_values.info'),
            value=True,
        ),

        BoolInput(
            name="check_duplicates",
            display_name=i18n.t('components.data.data_validator.check_duplicates.display_name'),
            info=i18n.t('components.data.data_validator.check_duplicates.info'),
            value=True,
        ),

        BoolInput(
            name="check_data_types",
            display_name=i18n.t('components.data.data_validator.check_data_types.display_name'),
            info=i18n.t('components.data.data_validator.check_data_types.info'),
            value=True,
        ),

        # Type validation schema
        MessageTextInput(
            name="type_schema",
            display_name=i18n.t('components.data.data_validator.type_schema.display_name'),
            info=i18n.t('components.data.data_validator.type_schema.info'),
            placeholder='{"id": "integer", "name": "string", "email": "email", "age": "integer"}',
            show=False,
            advanced=True,
        ),

        # Range validation
        BoolInput(
            name="check_ranges",
            display_name=i18n.t('components.data.data_validator.check_ranges.display_name'),
            info=i18n.t('components.data.data_validator.check_ranges.info'),
            value=False,
            advanced=True,
        ),

        MessageTextInput(
            name="range_schema",
            display_name=i18n.t('components.data.data_validator.range_schema.display_name'),
            info=i18n.t('components.data.data_validator.range_schema.info'),
            placeholder='{"age": {"min": 0, "max": 120}, "price": {"min": 0}}',
            show=False,
            advanced=True,
        ),

        # Custom validation rules
        BoolInput(
            name="use_custom_rules",
            display_name=i18n.t('components.data.data_validator.use_custom_rules.display_name'),
            info=i18n.t('components.data.data_validator.use_custom_rules.info'),
            value=False,
            advanced=True,
        ),

        MessageTextInput(
            name="custom_rules",
            display_name=i18n.t('components.data.data_validator.custom_rules.display_name'),
            info=i18n.t('components.data.data_validator.custom_rules.info'),
            placeholder='{"email_domain": {"field": "email", "pattern": ".*@company\\.com$"}}',
            show=False,
            advanced=True,
        ),

        # Output options
        BoolInput(
            name="include_statistics",
            display_name=i18n.t('components.data.data_validator.include_statistics.display_name'),
            info=i18n.t('components.data.data_validator.include_statistics.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="auto_clean",
            display_name=i18n.t('components.data.data_validator.auto_clean.display_name'),
            info=i18n.t('components.data.data_validator.auto_clean.info'),
            value=False,
            advanced=True,
        ),

        FloatInput(
            name="null_threshold",
            display_name=i18n.t('components.data.data_validator.null_threshold.display_name'),
            info=i18n.t('components.data.data_validator.null_threshold.info'),
            value=0.5,
            range_spec={"min": 0.0, "max": 1.0},
            show=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="validation_report",
            display_name=i18n.t('components.data.data_validator.outputs.validation_report.display_name'),
            method="validate_data"
        ),
        Output(
            name="clean_data",
            display_name=i18n.t('components.data.data_validator.outputs.clean_data.display_name'),
            method="get_clean_data"
        ),
        Output(
            name="error_records",
            display_name=i18n.t('components.data.data_validator.outputs.error_records.display_name'),
            method="get_error_records"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validation_results = None
        self._clean_data = None
        self._error_records = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on validation options."""
        if field_name == "check_data_types":
            build_config["type_schema"]["show"] = bool(field_value)
        elif field_name == "check_ranges":
            build_config["range_schema"]["show"] = bool(field_value)
        elif field_name == "use_custom_rules":
            build_config["custom_rules"]["show"] = bool(field_value)
        elif field_name == "auto_clean":
            build_config["null_threshold"]["show"] = bool(field_value)
        return build_config

    def validate_data(self) -> Data:
        """Main validation method that performs all checks and returns a validation report."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.data_validator.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.data_validator.errors.empty_data'))

            # Initialize validation results
            validation_results = {
                "summary": {
                    "total_records": len(data_list),
                    "valid_records": 0,
                    "invalid_records": 0,
                    "validation_timestamp": datetime.now().isoformat(),
                    "validation_mode": self.validation_mode,
                },
                "checks_performed": [],
                "errors": [],
                "warnings": [],
                "statistics": {}
            }

            # Perform validation checks
            valid_records = []
            error_records = []

            for idx, record in enumerate(data_list):
                record_errors = []

                # Check null values
                if self.check_null_values:
                    null_errors = self._check_null_values(record, idx)
                    record_errors.extend(null_errors)

                # Check data types
                if self.check_data_types and self.type_schema:
                    type_errors = self._check_data_types(record, idx)
                    record_errors.extend(type_errors)

                # Check ranges
                if self.check_ranges and self.range_schema:
                    range_errors = self._check_ranges(record, idx)
                    record_errors.extend(range_errors)

                # Check custom rules
                if self.use_custom_rules and self.custom_rules:
                    custom_errors = self._check_custom_rules(record, idx)
                    record_errors.extend(custom_errors)

                # Categorize record
                if record_errors:
                    validation_results["summary"]["invalid_records"] += 1
                    validation_results["errors"].extend(record_errors)
                    error_records.append({
                        "record_index": idx,
                        "data": record,
                        "errors": record_errors
                    })

                    # In strict mode, raise error immediately
                    if self.validation_mode == "strict":
                        error_msg = f"Validation failed at record {idx}: {record_errors[0]['message']}"
                        raise ValueError(error_msg)
                else:
                    validation_results["summary"]["valid_records"] += 1
                    valid_records.append(record)

            # Check for duplicates across all records
            if self.check_duplicates:
                duplicate_errors = self._check_duplicates(data_list)
                validation_results["errors"].extend(duplicate_errors)
                validation_results["checks_performed"].append("duplicate_check")

            # Update checks performed
            if self.check_null_values:
                validation_results["checks_performed"].append("null_value_check")
            if self.check_data_types:
                validation_results["checks_performed"].append("data_type_check")
            if self.check_ranges:
                validation_results["checks_performed"].append("range_check")
            if self.use_custom_rules:
                validation_results["checks_performed"].append("custom_rules_check")

            # Generate statistics
            if self.include_statistics:
                validation_results["statistics"] = self._generate_statistics(data_list)

            # Store results for other outputs
            self._validation_results = validation_results

            # Handle auto-cleaning
            if self.auto_clean:
                self._clean_data = self._perform_auto_clean(valid_records, error_records)
            else:
                self._clean_data = valid_records

            self._error_records = error_records

            # Create validation report
            report_text = self._format_validation_report(validation_results)

            self.status = f"Validation completed: {validation_results['summary']['valid_records']}/{validation_results['summary']['total_records']} records valid"

            return Data(
                text=report_text,
                data=validation_results
            )

        except Exception as e:
            error_message = i18n.t('components.data.data_validator.errors.validation_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_clean_data(self) -> list[Data]:
        """Return cleaned data records."""
        if self._clean_data is None:
            raise ValueError(i18n.t('components.data.data_validator.errors.no_validation_run'))

        return [Data(data=record) for record in self._clean_data]

    def get_error_records(self) -> list[Data]:
        """Return records that failed validation."""
        if self._error_records is None:
            raise ValueError(i18n.t('components.data.data_validator.errors.no_validation_run'))

        return [Data(data=record) for record in self._error_records]

    def _parse_input_data(self) -> list[dict]:
        """Parse input data from various formats."""
        if isinstance(self.data, list):
            # List of Data objects
            return [item.data if hasattr(item, 'data') else item for item in self.data]
        elif hasattr(self.data, 'data'):
            # Single Data object
            data_content = self.data.data
            if isinstance(data_content, list):
                return data_content
            else:
                return [data_content]
        elif isinstance(self.data, str):
            # JSON string
            try:
                parsed = json.loads(self.data)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                raise ValueError(i18n.t('components.data.data_validator.errors.invalid_json'))
        else:
            # Direct data
            return [self.data] if not isinstance(self.data, list) else self.data

    def _check_null_values(self, record: dict, record_idx: int) -> list[dict]:
        """Check for null/missing values in record."""
        errors = []
        for field, value in record.items():
            if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
                errors.append({
                    "type": "null_value",
                    "record_index": record_idx,
                    "field": field,
                    "message": f"Null or empty value found in field '{field}'"
                })
        return errors

    def _check_data_types(self, record: dict, record_idx: int) -> list[dict]:
        """Check data types against schema."""
        errors = []
        try:
            type_schema = json.loads(self.type_schema) if isinstance(self.type_schema, str) else self.type_schema
        except json.JSONDecodeError:
            return [{
                "type": "schema_error",
                "record_index": record_idx,
                "message": "Invalid type schema JSON"
            }]

        for field, expected_type in type_schema.items():
            if field not in record:
                continue

            value = record[field]
            if value is None:
                continue

            is_valid = self._validate_type(value, expected_type)
            if not is_valid:
                errors.append({
                    "type": "data_type",
                    "record_index": record_idx,
                    "field": field,
                    "expected_type": expected_type,
                    "actual_value": value,
                    "message": f"Field '{field}' expected {expected_type}, got {type(value).__name__}"
                })

        return errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate a single value against expected type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        elif expected_type == "float":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "email":
            if not isinstance(value, str):
                return False
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(email_pattern, value) is not None
        elif expected_type == "url":
            if not isinstance(value, str):
                return False
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            return re.match(url_pattern, value) is not None
        elif expected_type == "date":
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return True
                except ValueError:
                    return False
            return False
        else:
            return True  # Unknown types pass validation

    def _check_ranges(self, record: dict, record_idx: int) -> list[dict]:
        """Check numeric ranges against schema."""
        errors = []
        try:
            range_schema = json.loads(self.range_schema) if isinstance(self.range_schema, str) else self.range_schema
        except json.JSONDecodeError:
            return [{
                "type": "schema_error",
                "record_index": record_idx,
                "message": "Invalid range schema JSON"
            }]

        for field, range_config in range_schema.items():
            if field not in record:
                continue

            value = record[field]
            if value is None:
                continue

            try:
                numeric_value = float(value)

                if "min" in range_config and numeric_value < range_config["min"]:
                    errors.append({
                        "type": "range_violation",
                        "record_index": record_idx,
                        "field": field,
                        "value": numeric_value,
                        "constraint": f"min: {range_config['min']}",
                        "message": f"Field '{field}' value {numeric_value} is below minimum {range_config['min']}"
                    })

                if "max" in range_config and numeric_value > range_config["max"]:
                    errors.append({
                        "type": "range_violation",
                        "record_index": record_idx,
                        "field": field,
                        "value": numeric_value,
                        "constraint": f"max: {range_config['max']}",
                        "message": f"Field '{field}' value {numeric_value} exceeds maximum {range_config['max']}"
                    })

            except (ValueError, TypeError):
                errors.append({
                    "type": "range_error",
                    "record_index": record_idx,
                    "field": field,
                    "value": value,
                    "message": f"Field '{field}' value '{value}' is not numeric for range validation"
                })

        return errors

    def _check_custom_rules(self, record: dict, record_idx: int) -> list[dict]:
        """Check custom validation rules."""
        errors = []
        try:
            custom_rules = json.loads(self.custom_rules) if isinstance(self.custom_rules, str) else self.custom_rules
        except json.JSONDecodeError:
            return [{
                "type": "schema_error",
                "record_index": record_idx,
                "message": "Invalid custom rules JSON"
            }]

        for rule_name, rule_config in custom_rules.items():
            field = rule_config.get("field")
            if not field or field not in record:
                continue

            value = record[field]
            if value is None:
                continue

            # Pattern matching rule
            if "pattern" in rule_config:
                pattern = rule_config["pattern"]
                if not re.match(pattern, str(value)):
                    errors.append({
                        "type": "custom_rule",
                        "record_index": record_idx,
                        "field": field,
                        "rule_name": rule_name,
                        "value": value,
                        "pattern": pattern,
                        "message": f"Field '{field}' value '{value}' does not match pattern for rule '{rule_name}'"
                    })

            # Length rule
            if "min_length" in rule_config or "max_length" in rule_config:
                str_value = str(value)
                length = len(str_value)

                if "min_length" in rule_config and length < rule_config["min_length"]:
                    errors.append({
                        "type": "custom_rule",
                        "record_index": record_idx,
                        "field": field,
                        "rule_name": rule_name,
                        "value": value,
                        "constraint": f"min_length: {rule_config['min_length']}",
                        "message": f"Field '{field}' length {length} is below minimum {rule_config['min_length']}"
                    })

                if "max_length" in rule_config and length > rule_config["max_length"]:
                    errors.append({
                        "type": "custom_rule",
                        "record_index": record_idx,
                        "field": field,
                        "rule_name": rule_name,
                        "value": value,
                        "constraint": f"max_length: {rule_config['max_length']}",
                        "message": f"Field '{field}' length {length} exceeds maximum {rule_config['max_length']}"
                    })

        return errors

    def _check_duplicates(self, data_list: list[dict]) -> list[dict]:
        """Check for duplicate records."""
        errors = []
        seen_records = {}

        for idx, record in enumerate(data_list):
            # Create a hash of the record for duplicate detection
            record_key = json.dumps(record, sort_keys=True)

            if record_key in seen_records:
                errors.append({
                    "type": "duplicate",
                    "record_index": idx,
                    "duplicate_of": seen_records[record_key],
                    "message": f"Record {idx} is a duplicate of record {seen_records[record_key]}"
                })
            else:
                seen_records[record_key] = idx

        return errors

    def _generate_statistics(self, data_list: list[dict]) -> dict:
        """Generate data quality statistics."""
        if not data_list:
            return {}

        stats = {
            "record_count": len(data_list),
            "field_analysis": {},
            "data_quality_score": 0.0
        }

        # Analyze each field
        all_fields = set()
        for record in data_list:
            all_fields.update(record.keys())

        for field in all_fields:
            field_stats = {
                "total_count": 0,
                "null_count": 0,
                "unique_count": 0,
                "data_types": {},
                "null_percentage": 0.0
            }

            values = []
            for record in data_list:
                field_stats["total_count"] += 1
                value = record.get(field)

                if value is None or value == "":
                    field_stats["null_count"] += 1
                else:
                    values.append(value)
                    value_type = type(value).__name__
                    field_stats["data_types"][value_type] = field_stats["data_types"].get(value_type, 0) + 1

            field_stats["unique_count"] = len(set(str(v) for v in values))
            field_stats["null_percentage"] = (field_stats["null_count"] / field_stats["total_count"]) * 100

            stats["field_analysis"][field] = field_stats

        # Calculate overall data quality score
        total_fields = len(all_fields)
        quality_score = 0.0

        for field_stats in stats["field_analysis"].values():
            # Score based on completeness (non-null percentage)
            completeness_score = (1 - field_stats["null_percentage"] / 100) * 100
            quality_score += completeness_score

        stats["data_quality_score"] = quality_score / total_fields if total_fields > 0 else 0.0

        return stats

    def _perform_auto_clean(self, valid_records: list[dict], error_records: list[dict]) -> list[dict]:
        """Perform automatic data cleaning based on validation results."""
        cleaned_records = valid_records.copy()

        # Try to salvage some error records by cleaning them
        for error_record in error_records:
            record = error_record["data"].copy()
            errors = error_record["errors"]

            can_clean = True

            for error in errors:
                if error["type"] == "null_value":
                    # Remove null fields or set default values
                    field = error["field"]
                    if field in record:
                        del record[field]
                elif error["type"] == "data_type":
                    # Try to convert data types
                    field = error["field"]
                    expected_type = error["expected_type"]

                    if expected_type == "integer":
                        try:
                            record[field] = int(float(str(record[field])))
                        except (ValueError, TypeError):
                            can_clean = False
                            break
                    elif expected_type == "float":
                        try:
                            record[field] = float(record[field])
                        except (ValueError, TypeError):
                            can_clean = False
                            break
                    elif expected_type == "string":
                        record[field] = str(record[field])
                else:
                    # Cannot auto-clean other types of errors
                    can_clean = False
                    break

            if can_clean:
                cleaned_records.append(record)

        return cleaned_records

    def _format_validation_report(self, results: dict) -> str:
        """Format validation results into a readable report."""
        report_lines = []
        summary = results["summary"]

        report_lines.append("=== DATA VALIDATION REPORT ===")
        report_lines.append(f"Validation Timestamp: {summary['validation_timestamp']}")
        report_lines.append(f"Validation Mode: {summary['validation_mode']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Valid Records: {summary['valid_records']}")
        report_lines.append(f"  Invalid Records: {summary['invalid_records']}")

        if summary['total_records'] > 0:
            success_rate = (summary['valid_records'] / summary['total_records']) * 100
            report_lines.append(f"  Success Rate: {success_rate:.2f}%")

        report_lines.append("")
        report_lines.append(f"CHECKS PERFORMED: {', '.join(results['checks_performed'])}")

        if results["errors"]:
            report_lines.append("")
            report_lines.append("VALIDATION ERRORS:")
            error_counts = {}
            for error in results["errors"]:
                error_type = error["type"]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

            for error_type, count in error_counts.items():
                report_lines.append(f"  {error_type}: {count} occurrences")

        if "statistics" in results and results["statistics"]:
            stats = results["statistics"]
            report_lines.append("")
            report_lines.append("DATA QUALITY STATISTICS:")
            report_lines.append(f"  Overall Quality Score: {stats['data_quality_score']:.2f}%")

            if "field_analysis" in stats:
                report_lines.append("  Field Completeness:")
                for field, field_stats in stats["field_analysis"].items():
                    completeness = 100 - field_stats["null_percentage"]
                    report_lines.append(f"    {field}: {completeness:.1f}% complete")

        return "\n".join(report_lines)