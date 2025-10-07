import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union
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


class DataSplitterComponent(Component):
    display_name = i18n.t('components.data.data_splitter.display_name')
    description = i18n.t('components.data.data_splitter.description')
    icon = "scissors"
    name = "DataSplitter"

    inputs = [
        # Data input
        MessageTextInput(
            name="data",
            display_name=i18n.t('components.data.data_splitter.data.display_name'),
            info=i18n.t('components.data.data_splitter.data.info'),
            input_types=["Data"]
        ),

        # Split mode
        DropdownInput(
            name="split_mode",
            display_name=i18n.t('components.data.data_splitter.split_mode.display_name'),
            info=i18n.t('components.data.data_splitter.split_mode.info'),
            options=["random", "ratio", "sequential", "condition", "field_value", "chunk_size"],
            value="ratio",
            real_time_refresh=True,
        ),

        # Random split
        IntInput(
            name="random_seed",
            display_name=i18n.t('components.data.data_splitter.random_seed.display_name'),
            info=i18n.t('components.data.data_splitter.random_seed.info'),
            value=42,
            show=False,
            advanced=True,
        ),

        # Ratio split
        FloatInput(
            name="train_ratio",
            display_name=i18n.t('components.data.data_splitter.train_ratio.display_name'),
            info=i18n.t('components.data.data_splitter.train_ratio.info'),
            value=0.7,
            range_spec={"min": 0.0, "max": 1.0},
            show=True,
        ),

        FloatInput(
            name="validation_ratio",
            display_name=i18n.t('components.data.data_splitter.validation_ratio.display_name'),
            info=i18n.t('components.data.data_splitter.validation_ratio.info'),
            value=0.15,
            range_spec={"min": 0.0, "max": 1.0},
            show=True,
        ),

        FloatInput(
            name="test_ratio",
            display_name=i18n.t('components.data.data_splitter.test_ratio.display_name'),
            info=i18n.t('components.data.data_splitter.test_ratio.info'),
            value=0.15,
            range_spec={"min": 0.0, "max": 1.0},
            show=True,
        ),

        # Sequential split
        IntInput(
            name="sequence_position",
            display_name=i18n.t('components.data.data_splitter.sequence_position.display_name'),
            info=i18n.t('components.data.data_splitter.sequence_position.info'),
            value=100,
            show=False,
            advanced=True,
        ),

        # Condition split
        MessageTextInput(
            name="split_conditions",
            display_name=i18n.t('components.data.data_splitter.split_conditions.display_name'),
            info=i18n.t('components.data.data_splitter.split_conditions.info'),
            placeholder='[{"name": "high_score", "condition": "score >= 80"}, {"name": "medium_score", "condition": "score >= 60"}]',
            show=False,
            advanced=True,
        ),

        # Field value split
        StrInput(
            name="split_field",
            display_name=i18n.t('components.data.data_splitter.split_field.display_name'),
            info=i18n.t('components.data.data_splitter.split_field.info'),
            value="",
            show=False,
            advanced=True,
        ),

        # Chunk size split
        IntInput(
            name="chunk_size",
            display_name=i18n.t('components.data.data_splitter.chunk_size.display_name'),
            info=i18n.t('components.data.data_splitter.chunk_size.info'),
            value=100,
            range_spec={"min": 1, "max": 10000},
            show=False,
            advanced=True,
        ),

        # Advanced options
        BoolInput(
            name="shuffle_before_split",
            display_name=i18n.t('components.data.data_splitter.shuffle_before_split.display_name'),
            info=i18n.t('components.data.data_splitter.shuffle_before_split.info'),
            value=True,
            advanced=True,
        ),

        BoolInput(
            name="stratify_split",
            display_name=i18n.t('components.data.data_splitter.stratify_split.display_name'),
            info=i18n.t('components.data.data_splitter.stratify_split.info'),
            value=False,
            advanced=True,
        ),

        StrInput(
            name="stratify_field",
            display_name=i18n.t('components.data.data_splitter.stratify_field.display_name'),
            info=i18n.t('components.data.data_splitter.stratify_field.info'),
            value="",
            show=False,
            advanced=True,
        ),

        # Output options
        BoolInput(
            name="include_indices",
            display_name=i18n.t('components.data.data_splitter.include_indices.display_name'),
            info=i18n.t('components.data.data_splitter.include_indices.info'),
            value=False,
            advanced=True,
        ),

        BoolInput(
            name="include_split_info",
            display_name=i18n.t('components.data.data_splitter.include_split_info.display_name'),
            info=i18n.t('components.data.data_splitter.include_split_info.info'),
            value=True,
            advanced=True,
        ),

        DropdownInput(
            name="output_format",
            display_name=i18n.t('components.data.data_splitter.output_format.display_name'),
            info=i18n.t('components.data.data_splitter.output_format.info'),
            options=["separate_outputs", "combined_with_labels", "indexed_chunks"],
            value="separate_outputs",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="split_data",
            display_name=i18n.t('components.data.data_splitter.outputs.split_data.display_name'),
            method="split_data"
        ),
        Output(
            name="split_report",
            display_name=i18n.t('components.data.data_splitter.outputs.split_report.display_name'),
            method="get_split_report"
        ),
        Output(
            name="train_set",
            display_name=i18n.t('components.data.data_splitter.outputs.train_set.display_name'),
            method="get_train_set"
        ),
        Output(
            name="validation_set",
            display_name=i18n.t('components.data.data_splitter.outputs.validation_set.display_name'),
            method="get_validation_set"
        ),
        Output(
            name="test_set",
            display_name=i18n.t('components.data.data_splitter.outputs.test_set.display_name'),
            method="get_test_set"
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._split_report = None
        self._split_data = None
        self._train_set = None
        self._validation_set = None
        self._test_set = None

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Show/hide conditional fields based on split mode."""
        if field_name == "split_mode":
            # Hide all mode-specific fields first
            for field in ["train_ratio", "validation_ratio", "test_ratio", "random_seed", "sequence_position", "split_conditions", "split_field", "chunk_size"]:
                if field in build_config:
                    build_config[field]["show"] = False

            # Show relevant fields based on mode
            if field_value in ["ratio", "random"]:
                build_config["train_ratio"]["show"] = True
                build_config["validation_ratio"]["show"] = True
                build_config["test_ratio"]["show"] = True
                if field_value == "random":
                    build_config["random_seed"]["show"] = True
            elif field_value == "sequential":
                build_config["sequence_position"]["show"] = True
            elif field_value == "condition":
                build_config["split_conditions"]["show"] = True
            elif field_value == "field_value":
                build_config["split_field"]["show"] = True
            elif field_value == "chunk_size":
                build_config["chunk_size"]["show"] = True

        elif field_name == "stratify_split":
            build_config["stratify_field"]["show"] = bool(field_value)

        return build_config

    def split_data(self) -> list[Data]:
        """Main method to split data."""
        try:
            if not self.data:
                raise ValueError(i18n.t('components.data.data_splitter.errors.no_data'))

            # Parse input data
            data_list = self._parse_input_data()
            if not data_list:
                raise ValueError(i18n.t('components.data.data_splitter.errors.empty_data'))

            # Initialize split report
            split_report = {
                "summary": {
                    "total_records": len(data_list),
                    "split_mode": self.split_mode,
                    "processing_timestamp": datetime.now().isoformat(),
                    "shuffle_applied": self.shuffle_before_split,
                    "stratification_applied": self.stratify_split,
                },
                "splits": {},
                "statistics": {},
                "configuration": self._get_split_configuration()
            }

            # Shuffle data if requested
            if self.shuffle_before_split:
                import random
                random.seed(self.random_seed if hasattr(self, 'random_seed') else 42)
                data_list = data_list.copy()
                random.shuffle(data_list)

            # Perform split based on mode
            if self.split_mode == "ratio":
                splits = self._split_by_ratio(data_list)
            elif self.split_mode == "random":
                splits = self._split_randomly(data_list)
            elif self.split_mode == "sequential":
                splits = self._split_sequentially(data_list)
            elif self.split_mode == "condition":
                splits = self._split_by_condition(data_list)
            elif self.split_mode == "field_value":
                splits = self._split_by_field_value(data_list)
            elif self.split_mode == "chunk_size":
                splits = self._split_by_chunk_size(data_list)
            else:
                raise ValueError(f"Unknown split mode: {self.split_mode}")

            # Update split report
            split_report["splits"] = splits
            split_report["statistics"] = self._generate_split_statistics(splits, len(data_list))

            # Store individual sets
            self._train_set = splits.get("train", [])
            self._validation_set = splits.get("validation", [])
            self._test_set = splits.get("test", [])

            # Format output based on output_format
            formatted_output = self._format_output(splits, data_list)

            # Store results
            self._split_data = formatted_output
            self._split_report = Data(
                text=self._format_split_report(split_report),
                data=split_report
            )

            # Update status
            split_info = []
            for split_name, split_data in splits.items():
                split_info.append(f"{split_name}: {len(split_data)}")

            self.status = f"Split {len(data_list)} records into {len(splits)} sets - {', '.join(split_info)}"

            return self._split_data

        except Exception as e:
            error_message = i18n.t('components.data.data_splitter.errors.split_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_split_report(self) -> Data:
        """Return the split report."""
        if self._split_report is None:
            raise ValueError(i18n.t('components.data.data_splitter.errors.no_split_run'))
        return self._split_report

    def get_train_set(self) -> list[Data]:
        """Return the training set."""
        if self._train_set is None:
            raise ValueError(i18n.t('components.data.data_splitter.errors.no_split_run'))
        return [Data(data=record) for record in self._train_set]

    def get_validation_set(self) -> list[Data]:
        """Return the validation set."""
        if self._validation_set is None:
            raise ValueError(i18n.t('components.data.data_splitter.errors.no_split_run'))
        return [Data(data=record) for record in self._validation_set]

    def get_test_set(self) -> list[Data]:
        """Return the test set."""
        if self._test_set is None:
            raise ValueError(i18n.t('components.data.data_splitter.errors.no_split_run'))
        return [Data(data=record) for record in self._test_set]

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
                raise ValueError(i18n.t('components.data.data_splitter.errors.invalid_json'))
        else:
            return [self.data] if not isinstance(self.data, list) else self.data

    def _get_split_configuration(self) -> dict:
        """Get the current split configuration."""
        return {
            "split_mode": self.split_mode,
            "train_ratio": self.train_ratio if hasattr(self, 'train_ratio') else None,
            "validation_ratio": self.validation_ratio if hasattr(self, 'validation_ratio') else None,
            "test_ratio": self.test_ratio if hasattr(self, 'test_ratio') else None,
            "random_seed": self.random_seed if hasattr(self, 'random_seed') else None,
            "shuffle_before_split": self.shuffle_before_split,
            "stratify_split": self.stratify_split,
            "stratify_field": self.stratify_field if self.stratify_split else None,
        }

    def _split_by_ratio(self, data_list: list) -> dict:
        """Split data by specified ratios."""
        total_size = len(data_list)

        # Normalize ratios to ensure they sum to 1
        total_ratio = self.train_ratio + self.validation_ratio + self.test_ratio
        if total_ratio <= 0:
            raise ValueError("Total ratio must be greater than 0")

        # Calculate sizes
        train_size = int(total_size * (self.train_ratio / total_ratio))
        validation_size = int(total_size * (self.validation_ratio / total_ratio))
        test_size = total_size - train_size - validation_size  # Remaining goes to test

        # Apply stratification if requested
        if self.stratify_split and self.stratify_field:
            return self._stratified_split(data_list, train_size, validation_size, test_size)

        # Simple split
        splits = {}
        if train_size > 0:
            splits["train"] = data_list[:train_size]
        if validation_size > 0:
            splits["validation"] = data_list[train_size:train_size + validation_size]
        if test_size > 0:
            splits["test"] = data_list[train_size + validation_size:]

        return splits

    def _split_randomly(self, data_list: list) -> dict:
        """Split data randomly using the specified ratios."""
        import random

        # Set seed for reproducibility
        random.seed(self.random_seed)

        # Create shuffled copy
        shuffled_data = data_list.copy()
        random.shuffle(shuffled_data)

        # Use ratio split on shuffled data
        return self._split_by_ratio(shuffled_data)

    def _split_sequentially(self, data_list: list) -> dict:
        """Split data sequentially at specified position."""
        position = min(self.sequence_position, len(data_list))

        splits = {}
        if position > 0:
            splits["train"] = data_list[:position]
        if position < len(data_list):
            splits["test"] = data_list[position:]

        return splits

    def _split_by_condition(self, data_list: list) -> dict:
        """Split data based on conditional logic."""
        try:
            conditions = json.loads(self.split_conditions) if isinstance(self.split_conditions, str) else self.split_conditions or []
        except json.JSONDecodeError:
            conditions = []

        if not conditions:
            return {"all": data_list}

        splits = {}
        remaining_data = data_list.copy()

        for condition_rule in conditions:
            if not isinstance(condition_rule, dict):
                continue

            split_name = condition_rule.get("name", f"split_{len(splits)}")
            condition = condition_rule.get("condition", "")

            # Find records matching condition
            matching_records = []
            non_matching_records = []

            for record in remaining_data:
                if self._evaluate_condition(condition, record):
                    matching_records.append(record)
                else:
                    non_matching_records.append(record)

            if matching_records:
                splits[split_name] = matching_records

            remaining_data = non_matching_records

        # Add remaining data to "other" split if any
        if remaining_data:
            splits["other"] = remaining_data

        return splits

    def _split_by_field_value(self, data_list: list) -> dict:
        """Split data by unique values in a specific field."""
        if not self.split_field:
            return {"all": data_list}

        splits = {}

        for record in data_list:
            if not isinstance(record, dict) or self.split_field not in record:
                # Put records without the field in "missing" split
                if "missing" not in splits:
                    splits["missing"] = []
                splits["missing"].append(record)
                continue

            field_value = str(record[self.split_field])

            # Sanitize field value to use as split name
            split_name = re.sub(r'[^\w\-_]', '_', field_value)

            if split_name not in splits:
                splits[split_name] = []
            splits[split_name].append(record)

        return splits

    def _split_by_chunk_size(self, data_list: list) -> dict:
        """Split data into chunks of specified size."""
        chunk_size = max(1, self.chunk_size)
        splits = {}

        for i in range(0, len(data_list), chunk_size):
            chunk_num = i // chunk_size
            chunk_name = f"chunk_{chunk_num:03d}"
            splits[chunk_name] = data_list[i:i + chunk_size]

        return splits

    def _stratified_split(self, data_list: list, train_size: int, validation_size: int, test_size: int) -> dict:
        """Perform stratified split to maintain class distribution."""
        if not self.stratify_field:
            return self._split_by_ratio(data_list)

        # Group by stratify field
        groups = {}
        for record in data_list:
            if isinstance(record, dict) and self.stratify_field in record:
                key = str(record[self.stratify_field])
                if key not in groups:
                    groups[key] = []
                groups[key].append(record)

        if not groups:
            return self._split_by_ratio(data_list)

        # Split each group proportionally
        splits = {"train": [], "validation": [], "test": []}

        for group_records in groups.values():
            group_size = len(group_records)

            # Calculate group split sizes
            group_train = int(group_size * train_size / len(data_list))
            group_val = int(group_size * validation_size / len(data_list))
            group_test = group_size - group_train - group_val

            # Ensure minimum sizes
            group_train = max(0, group_train)
            group_val = max(0, group_val)
            group_test = max(0, group_test)

            if group_train > 0:
                splits["train"].extend(group_records[:group_train])
            if group_val > 0:
                splits["validation"].extend(group_records[group_train:group_train + group_val])
            if group_test > 0:
                splits["test"].extend(group_records[group_train + group_val:])

        return splits

    def _evaluate_condition(self, condition: str, record: dict) -> bool:
        """Evaluate a condition against a record."""
        if not condition or not isinstance(record, dict):
            return False

        # Replace field names with values
        eval_context = record.copy()

        # Simple condition evaluation
        for field, value in record.items():
            if isinstance(value, str):
                condition = condition.replace(field, f"'{value}'")
            else:
                condition = condition.replace(field, str(value))

        try:
            # Basic comparison operations
            for op in [">=", "<=", "==", "!=", ">", "<"]:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()

                        try:
                            left_val = eval(left) if left.startswith(("'", '"')) or left.replace('.', '').replace('-', '').isdigit() else left
                            right_val = eval(right) if right.startswith(("'", '"')) or right.replace('.', '').replace('-', '').isdigit() else right
                        except:
                            return False

                        if op == "==":
                            return str(left_val) == str(right_val)
                        elif op == "!=":
                            return str(left_val) != str(right_val)
                        elif op in [">", "<", ">=", "<="]:
                            try:
                                left_num = float(left_val)
                                right_num = float(right_val)
                                if op == ">":
                                    return left_num > right_num
                                elif op == "<":
                                    return left_num < right_num
                                elif op == ">=":
                                    return left_num >= right_num
                                elif op == "<=":
                                    return left_num <= right_num
                            except:
                                return False
        except:
            return False

        return False

    def _format_output(self, splits: dict, original_data: list) -> list[Data]:
        """Format the output based on output_format setting."""
        if self.output_format == "separate_outputs":
            # Return all splits combined
            all_splits = []
            for split_name, split_data in splits.items():
                for i, record in enumerate(split_data):
                    output_record = record.copy() if isinstance(record, dict) else record

                    if self.include_split_info:
                        if isinstance(output_record, dict):
                            output_record["_split"] = split_name

                    if self.include_indices:
                        if isinstance(output_record, dict):
                            # Find original index
                            try:
                                original_index = original_data.index(record)
                                output_record["_original_index"] = original_index
                            except ValueError:
                                output_record["_original_index"] = -1
                            output_record["_split_index"] = i

                    all_splits.append(Data(data=output_record))

            return all_splits

        elif self.output_format == "combined_with_labels":
            # Return data with split labels
            combined_data = []
            for split_name, split_data in splits.items():
                split_info = {
                    "split_name": split_name,
                    "split_size": len(split_data),
                    "data": split_data
                }
                combined_data.append(Data(data=split_info))

            return combined_data

        elif self.output_format == "indexed_chunks":
            # Return indexed chunks
            indexed_data = []
            for i, (split_name, split_data) in enumerate(splits.items()):
                chunk_info = {
                    "chunk_index": i,
                    "chunk_name": split_name,
                    "chunk_size": len(split_data),
                    "records": split_data
                }
                indexed_data.append(Data(data=chunk_info))

            return indexed_data

        else:
            # Default to separate outputs
            return self._format_output({"combined": list(splits.values())}, original_data)

    def _generate_split_statistics(self, splits: dict, total_records: int) -> dict:
        """Generate statistics about the split operation."""
        stats = {
            "split_count": len(splits),
            "split_distribution": {},
            "balance_score": 0.0,
            "coverage": 0.0
        }

        # Calculate distribution
        total_in_splits = 0
        for split_name, split_data in splits.items():
            split_size = len(split_data)
            stats["split_distribution"][split_name] = {
                "size": split_size,
                "percentage": (split_size / total_records) * 100 if total_records > 0 else 0
            }
            total_in_splits += split_size

        # Calculate coverage
        stats["coverage"] = (total_in_splits / total_records) * 100 if total_records > 0 else 0

        # Calculate balance score (how evenly distributed the splits are)
        if len(splits) > 1:
            sizes = [len(split_data) for split_data in splits.values()]
            avg_size = sum(sizes) / len(sizes)
            variance = sum((size - avg_size) ** 2 for size in sizes) / len(sizes)
            # Lower variance means better balance, normalize to 0-100 scale
            max_possible_variance = (max(sizes) - avg_size) ** 2
            stats["balance_score"] = (1 - (variance / max_possible_variance)) * 100 if max_possible_variance > 0 else 100
        else:
            stats["balance_score"] = 100  # Single split is perfectly balanced

        return stats

    def _format_split_report(self, report: dict) -> str:
        """Format the split report into readable text."""
        report_lines = []
        summary = report["summary"]

        report_lines.append("=== DATA SPLIT REPORT ===")
        report_lines.append(f"Processing Timestamp: {summary['processing_timestamp']}")
        report_lines.append(f"Split Mode: {summary['split_mode']}")
        report_lines.append(f"Total Records: {summary['total_records']}")
        report_lines.append("")

        # Split distribution
        if report["splits"]:
            report_lines.append("SPLIT DISTRIBUTION:")
            for split_name, split_data in report["splits"].items():
                size = len(split_data)
                percentage = (size / summary['total_records']) * 100 if summary['total_records'] > 0 else 0
                report_lines.append(f"  {split_name}: {size} records ({percentage:.1f}%)")

        # Statistics
        if "statistics" in report:
            stats = report["statistics"]
            report_lines.append("")
            report_lines.append("STATISTICS:")
            report_lines.append(f"  Number of Splits: {stats['split_count']}")
            report_lines.append(f"  Coverage: {stats['coverage']:.2f}%")
            report_lines.append(f"  Balance Score: {stats['balance_score']:.2f}%")

        # Configuration
        if "configuration" in report:
            config = report["configuration"]
            report_lines.append("")
            report_lines.append("CONFIGURATION:")
            for key, value in config.items():
                if value is not None:
                    report_lines.append(f"  {key}: {value}")

        # Processing options
        if summary.get("shuffle_applied"):
            report_lines.append(f"  Data Shuffled: Yes")
        if summary.get("stratification_applied"):
            report_lines.append(f"  Stratification Applied: Yes")

        return "\n".join(report_lines)