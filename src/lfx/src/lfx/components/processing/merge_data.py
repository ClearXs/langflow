from enum import Enum
from typing import cast
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame


class DataOperation(str, Enum):
    CONCATENATE = "Concatenate"
    APPEND = "Append"
    MERGE = "Merge"
    JOIN = "Join"


class MergeDataComponent(Component):
    display_name = i18n.t('components.processing.merge_data.display_name')
    description = i18n.t('components.processing.merge_data.description')
    icon = "merge"
    MIN_INPUTS_REQUIRED = 2
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="data_inputs",
            display_name=i18n.t(
                'components.processing.merge_data.data_inputs.display_name'),
            info=i18n.t('components.processing.merge_data.data_inputs.info'),
            is_list=True,
            required=True
        ),
        DropdownInput(
            name="operation",
            display_name=i18n.t(
                'components.processing.merge_data.operation.display_name'),
            options=[
                i18n.t('components.processing.merge_data.operations.concatenate'),
                i18n.t('components.processing.merge_data.operations.append'),
                i18n.t('components.processing.merge_data.operations.merge'),
                i18n.t('components.processing.merge_data.operations.join'),
            ],
            value=i18n.t(
                'components.processing.merge_data.operations.concatenate'),
            info=i18n.t('components.processing.merge_data.operation.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.merge_data.outputs.dataframe.display_name'),
            name="combined_data",
            method="combine_data"
        )
    ]

    def combine_data(self) -> DataFrame:
        try:
            # Validate inputs
            if not self.data_inputs:
                warning_msg = i18n.t(
                    'components.processing.merge_data.warnings.no_data_inputs')
                self.status = warning_msg
                return DataFrame()

            if len(self.data_inputs) < self.MIN_INPUTS_REQUIRED:
                warning_msg = i18n.t('components.processing.merge_data.warnings.insufficient_inputs',
                                     required=self.MIN_INPUTS_REQUIRED, provided=len(self.data_inputs))
                self.status = warning_msg
                return DataFrame()

            # Map localized operation names to internal enum values
            operation_map = {
                i18n.t('components.processing.merge_data.operations.concatenate'): DataOperation.CONCATENATE,
                i18n.t('components.processing.merge_data.operations.append'): DataOperation.APPEND,
                i18n.t('components.processing.merge_data.operations.merge'): DataOperation.MERGE,
                i18n.t('components.processing.merge_data.operations.join'): DataOperation.JOIN,
                # Also support English for backwards compatibility
                "Concatenate": DataOperation.CONCATENATE,
                "Append": DataOperation.APPEND,
                "Merge": DataOperation.MERGE,
                "Join": DataOperation.JOIN,
            }

            operation_enum = operation_map.get(
                self.operation, DataOperation.CONCATENATE)

            combined_dataframe = self._process_operation(operation_enum)

            success_msg = i18n.t('components.processing.merge_data.success.data_combined',
                                 operation=self.operation, inputs=len(
                                     self.data_inputs),
                                 rows=len(combined_dataframe))
            self.status = success_msg

            return combined_dataframe

        except Exception as e:
            error_msg = i18n.t('components.processing.merge_data.errors.combination_failed',
                               operation=self.operation, error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _process_operation(self, operation: DataOperation) -> DataFrame:
        """Process the specified data operation."""
        try:
            if operation == DataOperation.CONCATENATE:
                return self._concatenate_data()
            elif operation == DataOperation.APPEND:
                return self._append_data()
            elif operation == DataOperation.MERGE:
                return self._merge_data()
            elif operation == DataOperation.JOIN:
                return self._join_data()
            else:
                error_msg = i18n.t('components.processing.merge_data.errors.unsupported_operation',
                                   operation=operation.value)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = i18n.t('components.processing.merge_data.errors.operation_processing_failed',
                               operation=operation.value, error=str(e))
            raise ValueError(error_msg) from e

    def _concatenate_data(self) -> DataFrame:
        """Concatenate data by combining values for the same keys."""
        try:
            combined_data: dict[str, str | object] = {}

            for data_input in self.data_inputs:
                if not hasattr(data_input, 'data') or not isinstance(data_input.data, dict):
                    continue

                for key, value in data_input.data.items():
                    if key in combined_data:
                        # If both values are strings, concatenate with newline
                        if isinstance(combined_data[key], str) and isinstance(value, str):
                            combined_data[key] = f"{combined_data[key]}\n{value}"
                        else:
                            # Otherwise, replace with the new value
                            combined_data[key] = value
                    else:
                        combined_data[key] = value

            return DataFrame([combined_data])

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.merge_data.errors.concatenate_failed', error=str(e))
            raise ValueError(error_msg) from e

    def _append_data(self) -> DataFrame:
        """Append data as separate rows."""
        try:
            rows = []

            for data_input in self.data_inputs:
                if hasattr(data_input, 'data') and isinstance(data_input.data, dict):
                    rows.append(data_input.data)

            return DataFrame(rows)

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.merge_data.errors.append_failed', error=str(e))
            raise ValueError(error_msg) from e

    def _merge_data(self) -> DataFrame:
        """Merge data by collecting values for the same keys into lists."""
        try:
            result_data: dict[str, str | list[str] | object] = {}

            for data_input in self.data_inputs:
                if not hasattr(data_input, 'data') or not isinstance(data_input.data, dict):
                    continue

                for key, value in data_input.data.items():
                    if key in result_data and isinstance(value, str):
                        # If key already exists and value is string, create or extend list
                        if isinstance(result_data[key], list):
                            cast("list[str]", result_data[key]).append(value)
                        else:
                            result_data[key] = [result_data[key], value]
                    else:
                        result_data[key] = value

            return DataFrame([result_data])

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.merge_data.errors.merge_failed', error=str(e))
            raise ValueError(error_msg) from e

    def _join_data(self) -> DataFrame:
        """Join data by prefixing keys with document numbers."""
        try:
            combined_data = {}

            for idx, data_input in enumerate(self.data_inputs, 1):
                if not hasattr(data_input, 'data') or not isinstance(data_input.data, dict):
                    continue

                for key, value in data_input.data.items():
                    # Add document number suffix to avoid key conflicts (except for first document)
                    new_key = f"{key}_doc{idx}" if idx > 1 else key
                    combined_data[new_key] = value

            return DataFrame([combined_data])

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.merge_data.errors.join_failed', error=str(e))
            raise ValueError(error_msg) from e
