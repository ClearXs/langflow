import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Set, Union
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    MessageTextInput,
    StrInput,
    IntInput,
    Output
)
from lfx.schema.data import Data


class DeduplicatorComponent(Component):
    display_name = i18n.t('components.data.deduplicator.display_name')
    description = i18n.t('components.data.deduplicator.description')
    icon = "layers"
    name = "Deduplicator"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.deduplicator.data.display_name'),
            info=i18n.t('components.data.deduplicator.data.info'),
            input_types=["Data"]
        ),

        # Deduplication strategy
        DropdownInput(
            name="dedup_strategy",
            display_name=i18n.t('components.data.deduplicator.dedup_strategy.display_name'),
            info=i18n.t('components.data.deduplicator.dedup_strategy.info'),
            options=["full_record", "key_fields", "custom_hash", "fuzzy_match"],
            value="full_record",
            real_time_refresh=True,
        ),

        # Key fields for partial matching
        MessageTextInput(
            name="key_fields",
            display_name=i18n.t('components.data.deduplicator.key_fields.display_name'),
            info=i18n.t('components.data.deduplicator.key_fields.info'),
            placeholder='["id", "email", "name"]',
            show=False,
            advanced=True,
        ),

        # Custom hash fields
        MessageTextInput(
            name="hash_fields",
            display_name=i18n.t('components.data.deduplicator.hash_fields.display_name'),
            info=i18n.t('components.data.deduplicator.hash_fields.info'),
            placeholder='["field1", "field2"]',
            show=False,
            advanced=True,
        ),

        # Fuzzy matching configuration
        MessageTextInput(
            name="fuzzy_config",
            display_name=i18n.t('components.data.deduplicator.fuzzy_config.display_name'),
            info=i18n.t('components.data.deduplicator.fuzzy_config.info'),
            placeholder='{"similarity_threshold": 0.8, "fields": ["name", "email"]}',
            show=False,
            advanced=True,
        ),

        # Duplicate handling
        DropdownInput(
            name="keep_strategy",
            display_name=i18n.t('components.data.deduplicator.keep_strategy.display_name'),
            info=i18n.t('components.data.deduplicator.keep_strategy.info'),
            options=["first", "last", "most_complete", "custom_priority"],
            value="first",
            advanced=True,
        ),

        # Priority fields for custom strategy
        MessageTextInput(
            name="priority_fields",
            display_name=i18n.t('components.data.deduplicator.priority_fields.display_name'),
            info=i18n.t('components.data.deduplicator.priority_fields.info'),
            placeholder='["updated_at", "created_at", "score"]',
            show=False,
            advanced=True,
        ),

        # Case sensitivity
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t('components.data.deduplicator.case_sensitive.display_name'),
            info=i18n.t('components.data.deduplicator.case_sensitive.info'),
            value=True,
            advanced=True,
        ),

        # Ignore whitespace
        BoolInput(
            name="ignore_whitespace",
            display_name=i18n.t('components.data.deduplicator.ignore_whitespace.display_name'),
            info=i18n.t('components.data.deduplicator.ignore_whitespace.info'),
            value=False,
            advanced=True,
        ),

        # Output options
        BoolInput(
            name="include_duplicate_info",
            display_name=i18n.t('components.data.deduplicator.include_duplicate_info.display_name'),
            info=i18n.t('components.data.deduplicator.include_duplicate_info.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="preserve_order",
            display_name=i18n.t('components.data.deduplicator.preserve_order.display_name'),
            info=i18n.t('components.data.deduplicator.preserve_order.info'),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="deduplicated_data",
            display_name=i18n.t('components.data.deduplicator.outputs.deduplicated_data.display_name'),
            method="deduplicate_data"
        ),
        Output(
            name="duplicate_report",
            display_name=i18n.t('components.data.deduplicator.outputs.duplicate_report.display_name'),
            method="get_duplicate_report"
        ),
        Output(
            name="duplicate_records",
            display_name=i18n.t('components.data.deduplicator.outputs.duplicate_records.display_name'),
            method="get_duplicate_records"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._duplicate_report = None
        self._duplicate_records = None
        self._deduplicated_data = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on strategy selection."""
        if field_name == "dedup_strategy":
            # Reset all visibility
            for field in ["key_fields", "hash_fields", "fuzzy_config"]:
                if field in build_config:
                    build_config[field]["show"] = False

            # Show relevant fields based on strategy
            if field_value == "key_fields":
                build_config["key_fields"]["show"] = True
            elif field_value == "custom_hash":
                build_config["hash_fields"]["show"] = True
            elif field_value == "fuzzy_match":
                build_config["fuzzy_config"]["show"] = True

        elif field_name == "keep_strategy":
            build_config["priority_fields"]["show"] = (field_value == "custom_priority")

        return build_config

    def deduplicate_data(self) -> list[Data]:
        """Main method to deduplicate data."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.deduplicator.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.deduplicator.errors.empty_data'))

            # Initialize deduplication report
            dedup_report = {
                "summary": {
                    "total_records": len(data_list),
                    "unique_records": 0,
                    "duplicate_records": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "strategy": self.dedup_strategy,
                    "keep_strategy": self.keep_strategy,
                },
                "duplicate_groups": [],
                "field_analysis": {},
                "statistics": {}
            }

            # Deduplicate based on strategy
            if self.dedup_strategy == "full_record":
                unique_data, duplicates = self._deduplicate_full_record(data_list)
            elif self.dedup_strategy == "key_fields":
                unique_data, duplicates = self._deduplicate_key_fields(data_list)
            elif self.dedup_strategy == "custom_hash":
                unique_data, duplicates = self._deduplicate_custom_hash(data_list)
            elif self.dedup_strategy == "fuzzy_match":
                unique_data, duplicates = self._deduplicate_fuzzy_match(data_list)
            else:
                raise ValueError(f"Unknown deduplication strategy: {self.dedup_strategy}")

            # Update report
            dedup_report["summary"]["unique_records"] = len(unique_data)
            dedup_report["summary"]["duplicate_records"] = len(data_list) - len(unique_data)
            dedup_report["duplicate_groups"] = duplicates

            # Generate field analysis and statistics
            if self.include_duplicate_info:
                dedup_report["field_analysis"] = self._analyze_duplicate_fields(data_list, duplicates)
                dedup_report["statistics"] = self._generate_dedup_statistics(dedup_report)

            # Store results
            self._deduplicated_data = [Data(data=record, text_key=getattr(self.data[0], 'text_key', 'text') if hasattr(self.data, '__iter__') and self.data else 'text') for record in unique_data]
            self._duplicate_report = Data(
                text=self._format_duplicate_report(dedup_report),
                data=dedup_report
            )
            self._duplicate_records = [Data(data=dup_group) for dup_group in duplicates]

            # Update status
            duplicate_rate = (dedup_report["summary"]["duplicate_records"] / dedup_report["summary"]["total_records"]) * 100
            self.status = f"Removed {dedup_report['summary']['duplicate_records']} duplicates ({duplicate_rate:.1f}%) from {dedup_report['summary']['total_records']} records"

            return self._deduplicated_data

        except Exception as e:
            error_message = i18n.t('components.data.deduplicator.errors.dedup_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_duplicate_report(self) -> Data:
        """Return the deduplication report."""
        if self._duplicate_report is None:
            raise ValueError(i18n.t('components.data.deduplicator.errors.no_dedup_run'))
        return self._duplicate_report

    def get_duplicate_records(self) -> list[Data]:
        """Return the duplicate record groups."""
        if self._duplicate_records is None:
            raise ValueError(i18n.t('components.data.deduplicator.errors.no_dedup_run'))
        return self._duplicate_records

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
                raise ValueError(i18n.t('components.data.deduplicator.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value based on configuration settings."""
        if isinstance(value, str):
            if not self.case_sensitive:
                value = value.lower()
            if self.ignore_whitespace:
                value = value.strip()
        return value

    def _create_record_hash(self, record: dict, fields: list = None) -> str:
        """Create a hash for a record based on specified fields."""
        if fields is None:
            # Use all fields
            hash_data = record
        else:
            # Use only specified fields
            hash_data = {k: v for k, v in record.items() if k in fields}

        # Normalize values
        normalized_data = {}
        for k, v in hash_data.items():
            normalized_data[k] = self._normalize_value(v)

        # Create hash
        record_str = json.dumps(normalized_data, sort_keys=True, default=str)
        return hashlib.md5(record_str.encode()).hexdigest()

    def _deduplicate_full_record(self, data_list: list[dict]) -> tuple[list[dict], list[dict]]:
        """Deduplicate based on full record comparison."""
        seen_hashes = {}
        unique_records = []
        duplicate_groups = []

        for idx, record in enumerate(data_list):
            record_hash = self._create_record_hash(record)

            if record_hash not in seen_hashes:
                seen_hashes[record_hash] = {
                    "first_index": idx,
                    "record": record,
                    "duplicates": []
                }
                unique_records.append(record)
            else:
                # This is a duplicate
                original_info = seen_hashes[record_hash]
                original_info["duplicates"].append({
                    "index": idx,
                    "record": record
                })

        # Extract duplicate groups
        for hash_key, info in seen_hashes.items():
            if info["duplicates"]:
                duplicate_group = {
                    "hash": hash_key,
                    "original": {
                        "index": info["first_index"],
                        "record": info["record"]
                    },
                    "duplicates": info["duplicates"],
                    "total_count": len(info["duplicates"]) + 1
                }
                duplicate_groups.append(duplicate_group)

        return self._apply_keep_strategy(unique_records, duplicate_groups), duplicate_groups

    def _deduplicate_key_fields(self, data_list: list[dict]) -> tuple[list[dict], list[dict]]:
        """Deduplicate based on specific key fields."""
        try:
            key_fields = json.loads(self.key_fields) if isinstance(self.key_fields, str) else self.key_fields
        except (json.JSONDecodeError, TypeError):
            key_fields = []

        if not key_fields:
            raise ValueError("Key fields must be specified for key_fields strategy")

        seen_combinations = {}
        unique_records = []
        duplicate_groups = []

        for idx, record in enumerate(data_list):
            # Extract key field values
            key_values = {}
            for field in key_fields:
                if field in record:
                    key_values[field] = self._normalize_value(record[field])

            key_hash = self._create_record_hash(key_values)

            if key_hash not in seen_combinations:
                seen_combinations[key_hash] = {
                    "first_index": idx,
                    "record": record,
                    "duplicates": [],
                    "key_values": key_values
                }
                unique_records.append(record)
            else:
                original_info = seen_combinations[key_hash]
                original_info["duplicates"].append({
                    "index": idx,
                    "record": record
                })

        # Extract duplicate groups
        for key_hash, info in seen_combinations.items():
            if info["duplicates"]:
                duplicate_group = {
                    "key_hash": key_hash,
                    "key_fields": key_fields,
                    "key_values": info["key_values"],
                    "original": {
                        "index": info["first_index"],
                        "record": info["record"]
                    },
                    "duplicates": info["duplicates"],
                    "total_count": len(info["duplicates"]) + 1
                }
                duplicate_groups.append(duplicate_group)

        return self._apply_keep_strategy(unique_records, duplicate_groups), duplicate_groups

    def _deduplicate_custom_hash(self, data_list: list[dict]) -> tuple[list[dict], list[dict]]:
        """Deduplicate based on custom hash fields."""
        try:
            hash_fields = json.loads(self.hash_fields) if isinstance(self.hash_fields, str) else self.hash_fields
        except (json.JSONDecodeError, TypeError):
            hash_fields = []

        if not hash_fields:
            raise ValueError("Hash fields must be specified for custom_hash strategy")

        seen_hashes = {}
        unique_records = []
        duplicate_groups = []

        for idx, record in enumerate(data_list):
            record_hash = self._create_record_hash(record, hash_fields)

            if record_hash not in seen_hashes:
                seen_hashes[record_hash] = {
                    "first_index": idx,
                    "record": record,
                    "duplicates": []
                }
                unique_records.append(record)
            else:
                original_info = seen_hashes[record_hash]
                original_info["duplicates"].append({
                    "index": idx,
                    "record": record
                })

        # Extract duplicate groups
        for hash_key, info in seen_hashes.items():
            if info["duplicates"]:
                duplicate_group = {
                    "hash": hash_key,
                    "hash_fields": hash_fields,
                    "original": {
                        "index": info["first_index"],
                        "record": info["record"]
                    },
                    "duplicates": info["duplicates"],
                    "total_count": len(info["duplicates"]) + 1
                }
                duplicate_groups.append(duplicate_group)

        return self._apply_keep_strategy(unique_records, duplicate_groups), duplicate_groups

    def _deduplicate_fuzzy_match(self, data_list: list[dict]) -> tuple[list[dict], list[dict]]:
        """Deduplicate based on fuzzy string matching."""
        try:
            fuzzy_config = json.loads(self.fuzzy_config) if isinstance(self.fuzzy_config, str) else self.fuzzy_config or {}
        except json.JSONDecodeError:
            fuzzy_config = {}

        threshold = fuzzy_config.get("similarity_threshold", 0.8)
        compare_fields = fuzzy_config.get("fields", [])

        if not compare_fields:
            raise ValueError("Fields must be specified for fuzzy matching")

        unique_records = []
        duplicate_groups = []
        processed_indices = set()

        for i, record1 in enumerate(data_list):
            if i in processed_indices:
                continue

            # This record will be kept as unique
            unique_records.append(record1)
            current_group = {
                "similarity_threshold": threshold,
                "compare_fields": compare_fields,
                "original": {
                    "index": i,
                    "record": record1
                },
                "duplicates": [],
                "total_count": 1
            }

            # Compare with remaining records
            for j, record2 in enumerate(data_list[i+1:], i+1):
                if j in processed_indices:
                    continue

                # Calculate similarity
                similarity = self._calculate_similarity(record1, record2, compare_fields)

                if similarity >= threshold:
                    current_group["duplicates"].append({
                        "index": j,
                        "record": record2,
                        "similarity": similarity
                    })
                    current_group["total_count"] += 1
                    processed_indices.add(j)

            # Add to duplicate groups if duplicates found
            if current_group["duplicates"]:
                duplicate_groups.append(current_group)

            processed_indices.add(i)

        return self._apply_keep_strategy(unique_records, duplicate_groups), duplicate_groups

    def _calculate_similarity(self, record1: dict, record2: dict, fields: list) -> float:
        """Calculate similarity between two records based on specified fields."""
        similarities = []

        for field in fields:
            if field not in record1 or field not in record2:
                similarities.append(0.0)
                continue

            val1 = str(record1[field]).lower() if not self.case_sensitive else str(record1[field])
            val2 = str(record2[field]).lower() if not self.case_sensitive else str(record2[field])

            if self.ignore_whitespace:
                val1 = val1.strip()
                val2 = val2.strip()

            # Simple string similarity using Levenshtein-like approach
            similarity = self._string_similarity(val1, val2)
            similarities.append(similarity)

        # Return average similarity
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using a simple algorithm."""
        if s1 == s2:
            return 1.0

        if not s1 or not s2:
            return 0.0

        # Simple character-based similarity
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s2 if longer == s1 else s1

        longer_len = len(longer)
        if longer_len == 0:
            return 1.0

        # Calculate character overlap
        matches = 0
        for i, char in enumerate(shorter):
            if i < len(longer) and char == longer[i]:
                matches += 1

        return matches / longer_len

    def _apply_keep_strategy(self, unique_records: list[dict], duplicate_groups: list[dict]) -> list[dict]:
        """Apply the keep strategy to determine which record to keep from duplicates."""
        if self.keep_strategy == "first":
            return unique_records  # Already keeping first by default

        final_records = []

        for record in unique_records:
            # Find corresponding duplicate group
            record_group = None
            for group in duplicate_groups:
                if group["original"]["record"] == record:
                    record_group = group
                    break

            if not record_group:
                # No duplicates, keep original
                final_records.append(record)
                continue

            # Apply keep strategy
            if self.keep_strategy == "last":
                # Keep the last duplicate
                if record_group["duplicates"]:
                    final_records.append(record_group["duplicates"][-1]["record"])
                else:
                    final_records.append(record)

            elif self.keep_strategy == "most_complete":
                # Keep the record with most non-null fields
                all_records = [record_group["original"]["record"]] + [dup["record"] for dup in record_group["duplicates"]]
                best_record = max(all_records, key=lambda r: sum(1 for v in r.values() if v is not None and v != ""))
                final_records.append(best_record)

            elif self.keep_strategy == "custom_priority":
                # Keep based on priority fields
                try:
                    priority_fields = json.loads(self.priority_fields) if isinstance(self.priority_fields, str) else self.priority_fields or []
                except json.JSONDecodeError:
                    priority_fields = []

                if priority_fields:
                    all_records = [record_group["original"]["record"]] + [dup["record"] for dup in record_group["duplicates"]]
                    best_record = self._get_highest_priority_record(all_records, priority_fields)
                    final_records.append(best_record)
                else:
                    final_records.append(record)  # Fallback to original

            else:
                final_records.append(record)

        return final_records

    def _get_highest_priority_record(self, records: list[dict], priority_fields: list) -> dict:
        """Get the record with highest priority based on priority fields."""
        def priority_score(record: dict) -> tuple:
            scores = []
            for field in priority_fields:
                value = record.get(field)
                if value is None:
                    scores.append(0)
                elif isinstance(value, (int, float)):
                    scores.append(value)
                elif isinstance(value, str):
                    try:
                        # Try to parse as number
                        scores.append(float(value))
                    except ValueError:
                        # Use string length as fallback
                        scores.append(len(value))
                else:
                    scores.append(0)
            return tuple(scores)

        return max(records, key=priority_score)

    def _analyze_duplicate_fields(self, data_list: list[dict], duplicate_groups: list[dict]) -> dict:
        """Analyze which fields contribute most to duplicates."""
        field_analysis = {}

        # Get all fields
        all_fields = set()
        for record in data_list:
            all_fields.update(record.keys())

        for field in all_fields:
            field_analysis[field] = {
                "total_records": 0,
                "duplicate_records": 0,
                "unique_values": set(),
                "duplicate_contribution": 0.0
            }

        # Analyze each record
        for record in data_list:
            for field in all_fields:
                if field in record:
                    field_analysis[field]["total_records"] += 1
                    field_analysis[field]["unique_values"].add(str(record[field]))

        # Analyze duplicates
        for group in duplicate_groups:
            all_records_in_group = [group["original"]["record"]] + [dup["record"] for dup in group["duplicates"]]

            for field in all_fields:
                # Check if this field has identical values across duplicates
                values = [record.get(field) for record in all_records_in_group if field in record]
                if len(set(str(v) for v in values)) == 1:  # All same value
                    field_analysis[field]["duplicate_contribution"] += len(all_records_in_group) - 1

        # Calculate percentages
        for field, analysis in field_analysis.items():
            if analysis["total_records"] > 0:
                analysis["uniqueness_ratio"] = len(analysis["unique_values"]) / analysis["total_records"]
                analysis["duplicate_records"] = analysis["duplicate_contribution"]
                analysis["unique_values"] = len(analysis["unique_values"])  # Convert set to count

        return field_analysis

    def _generate_dedup_statistics(self, dedup_report: dict) -> dict:
        """Generate comprehensive deduplication statistics."""
        stats = {
            "deduplication_rate": 0.0,
            "duplicate_rate": 0.0,
            "average_duplicates_per_group": 0.0,
            "largest_duplicate_group": 0,
            "strategy_effectiveness": {}
        }

        summary = dedup_report["summary"]
        total_records = summary["total_records"]
        unique_records = summary["unique_records"]
        duplicate_records = summary["duplicate_records"]

        if total_records > 0:
            stats["deduplication_rate"] = (duplicate_records / total_records) * 100
            stats["duplicate_rate"] = (duplicate_records / total_records) * 100

        # Analyze duplicate groups
        duplicate_groups = dedup_report["duplicate_groups"]
        if duplicate_groups:
            group_sizes = [group["total_count"] for group in duplicate_groups]
            stats["average_duplicates_per_group"] = sum(group_sizes) / len(group_sizes)
            stats["largest_duplicate_group"] = max(group_sizes)
            stats["total_duplicate_groups"] = len(duplicate_groups)

        # Strategy effectiveness
        stats["strategy_effectiveness"] = {
            "strategy_used": summary["strategy"],
            "records_processed": total_records,
            "records_removed": duplicate_records,
            "efficiency_score": (duplicate_records / total_records * 100) if total_records > 0 else 0
        }

        return stats

    def _format_duplicate_report(self, dedup_report: dict) -> str:
        """Format the deduplication report into readable text."""
        report_lines = []
        summary = dedup_report["summary"]

        report_lines.append("=== DEDUPLICATION REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Strategy: {summary['strategy']}")
        report_lines.append(f"Keep Strategy: {summary['keep_strategy']}")
        report_lines.append("")

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Records: {summary['total_records']}")
        report_lines.append(f"  Unique Records: {summary['unique_records']}")
        report_lines.append(f"  Duplicate Records: {summary['duplicate_records']}")

        if summary['total_records'] > 0:
            dedup_rate = (summary['duplicate_records'] / summary['total_records']) * 100
            report_lines.append(f"  Deduplication Rate: {dedup_rate:.2f}%")

        # Duplicate groups summary
        if dedup_report["duplicate_groups"]:
            report_lines.append("")
            report_lines.append("DUPLICATE GROUPS:")
            report_lines.append(f"  Total Groups: {len(dedup_report['duplicate_groups'])}")

            group_sizes = [group["total_count"] for group in dedup_report["duplicate_groups"]]
            report_lines.append(f"  Largest Group Size: {max(group_sizes)}")
            report_lines.append(f"  Average Group Size: {sum(group_sizes) / len(group_sizes):.1f}")

        # Statistics
        if "statistics" in dedup_report and dedup_report["statistics"]:
            stats = dedup_report["statistics"]
            report_lines.append("")
            report_lines.append("STATISTICS:")
            report_lines.append(f"  Efficiency Score: {stats['strategy_effectiveness']['efficiency_score']:.2f}%")

        # Field analysis
        if "field_analysis" in dedup_report and dedup_report["field_analysis"]:
            report_lines.append("")
            report_lines.append("FIELD ANALYSIS:")
            for field, analysis in dedup_report["field_analysis"].items():
                if analysis.get("duplicate_contribution", 0) > 0:
                    report_lines.append(f"  {field}:")
                    report_lines.append(f"    Uniqueness Ratio: {analysis.get('uniqueness_ratio', 0):.3f}")
                    report_lines.append(f"    Duplicate Contribution: {analysis.get('duplicate_contribution', 0)}")

        return "\n".join(report_lines)