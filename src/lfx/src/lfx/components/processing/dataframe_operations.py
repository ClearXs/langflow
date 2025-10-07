import pandas as pd
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs import SortableListInput
from lfx.io import BoolInput, DataFrameInput, DropdownInput, IntInput, MessageTextInput, Output, StrInput
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame


class DataFrameOperationsComponent(Component):
    display_name = i18n.t(
        'components.processing.dataframe_operations.display_name')
    description = i18n.t(
        'components.processing.dataframe_operations.description')
    documentation: str = "https://docs.langflow.org/components-processing#dataframe-operations"
    icon = "table"
    name = "DataFrameOperations"

    OPERATION_CHOICES = [
        "Add Column",
        "Drop Column",
        "Filter",
        "Head",
        "Rename Column",
        "Replace Value",
        "Select Columns",
        "Sort",
        "Tail",
        "Drop Duplicates",
    ]

    inputs = [
        DataFrameInput(
            name="df",
            display_name=i18n.t(
                'components.processing.dataframe_operations.df.display_name'),
            info=i18n.t('components.processing.dataframe_operations.df.info'),
            required=True,
        ),
        SortableListInput(
            name="operation",
            display_name=i18n.t(
                'components.processing.dataframe_operations.operation.display_name'),
            placeholder=i18n.t(
                'components.processing.dataframe_operations.operation.placeholder'),
            info=i18n.t(
                'components.processing.dataframe_operations.operation.info'),
            options=[
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.add_column'), "icon": "plus"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.drop_column'), "icon": "minus"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.filter'), "icon": "filter"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.head'), "icon": "arrow-up"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.rename_column'), "icon": "pencil"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.replace_value'), "icon": "replace"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.select_columns'), "icon": "columns"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.sort'), "icon": "arrow-up-down"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.tail'), "icon": "arrow-down"},
                {"name": i18n.t(
                    'components.processing.dataframe_operations.operations.drop_duplicates'), "icon": "copy-x"},
            ],
            real_time_refresh=True,
            limit=1,
        ),
        StrInput(
            name="column_name",
            display_name=i18n.t(
                'components.processing.dataframe_operations.column_name.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.column_name.info'),
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="filter_value",
            display_name=i18n.t(
                'components.processing.dataframe_operations.filter_value.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.filter_value.info'),
            dynamic=True,
            show=False,
        ),
        DropdownInput(
            name="filter_operator",
            display_name=i18n.t(
                'components.processing.dataframe_operations.filter_operator.display_name'),
            options=[
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.equals'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.not_equals'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.contains'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.not_contains'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.starts_with'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.ends_with'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.greater_than'),
                i18n.t(
                    'components.processing.dataframe_operations.filter_operators.less_than'),
            ],
            value=i18n.t(
                'components.processing.dataframe_operations.filter_operators.equals'),
            info=i18n.t(
                'components.processing.dataframe_operations.filter_operator.info'),
            advanced=False,
            dynamic=True,
            show=False,
        ),
        BoolInput(
            name="ascending",
            display_name=i18n.t(
                'components.processing.dataframe_operations.ascending.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.ascending.info'),
            dynamic=True,
            show=False,
            value=True,
        ),
        StrInput(
            name="new_column_name",
            display_name=i18n.t(
                'components.processing.dataframe_operations.new_column_name.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.new_column_name.info'),
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="new_column_value",
            display_name=i18n.t(
                'components.processing.dataframe_operations.new_column_value.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.new_column_value.info'),
            dynamic=True,
            show=False,
        ),
        StrInput(
            name="columns_to_select",
            display_name=i18n.t(
                'components.processing.dataframe_operations.columns_to_select.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.columns_to_select.info'),
            dynamic=True,
            is_list=True,
            show=False,
        ),
        IntInput(
            name="num_rows",
            display_name=i18n.t(
                'components.processing.dataframe_operations.num_rows.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.num_rows.info'),
            dynamic=True,
            show=False,
            value=5,
        ),
        MessageTextInput(
            name="replace_value",
            display_name=i18n.t(
                'components.processing.dataframe_operations.replace_value.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.replace_value.info'),
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="replacement_value",
            display_name=i18n.t(
                'components.processing.dataframe_operations.replacement_value.display_name'),
            info=i18n.t(
                'components.processing.dataframe_operations.replacement_value.info'),
            dynamic=True,
            show=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.dataframe_operations.outputs.dataframe.display_name'),
            name="output",
            method="perform_operation",
            info=i18n.t(
                'components.processing.dataframe_operations.outputs.dataframe.info'),
        )
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        dynamic_fields = [
            "column_name",
            "filter_value",
            "filter_operator",
            "ascending",
            "new_column_name",
            "new_column_value",
            "columns_to_select",
            "num_rows",
            "replace_value",
            "replacement_value",
        ]
        for field in dynamic_fields:
            build_config[field]["show"] = False

        if field_name == "operation":
            # Handle SortableListInput format
            if isinstance(field_value, list):
                operation_name = field_value[0].get(
                    "name", "") if field_value else ""
            else:
                operation_name = field_value or ""

            # If no operation selected, all dynamic fields stay hidden (already set to False above)
            if not operation_name:
                return build_config

            # Map localized operation names to internal names
            operation_map = {
                i18n.t('components.processing.dataframe_operations.operations.add_column'): "Add Column",
                i18n.t('components.processing.dataframe_operations.operations.drop_column'): "Drop Column",
                i18n.t('components.processing.dataframe_operations.operations.filter'): "Filter",
                i18n.t('components.processing.dataframe_operations.operations.head'): "Head",
                i18n.t('components.processing.dataframe_operations.operations.rename_column'): "Rename Column",
                i18n.t('components.processing.dataframe_operations.operations.replace_value'): "Replace Value",
                i18n.t('components.processing.dataframe_operations.operations.select_columns'): "Select Columns",
                i18n.t('components.processing.dataframe_operations.operations.sort'): "Sort",
                i18n.t('components.processing.dataframe_operations.operations.tail'): "Tail",
                i18n.t('components.processing.dataframe_operations.operations.drop_duplicates'): "Drop Duplicates",
                # Also support English names for backwards compatibility
                "Add Column": "Add Column",
                "Drop Column": "Drop Column",
                "Filter": "Filter",
                "Head": "Head",
                "Rename Column": "Rename Column",
                "Replace Value": "Replace Value",
                "Select Columns": "Select Columns",
                "Sort": "Sort",
                "Tail": "Tail",
                "Drop Duplicates": "Drop Duplicates",
            }

            internal_operation = operation_map.get(
                operation_name, operation_name)

            if internal_operation == "Filter":
                build_config["column_name"]["show"] = True
                build_config["filter_value"]["show"] = True
                build_config["filter_operator"]["show"] = True
            elif internal_operation == "Sort":
                build_config["column_name"]["show"] = True
                build_config["ascending"]["show"] = True
            elif internal_operation == "Drop Column":
                build_config["column_name"]["show"] = True
            elif internal_operation == "Rename Column":
                build_config["column_name"]["show"] = True
                build_config["new_column_name"]["show"] = True
            elif internal_operation == "Add Column":
                build_config["new_column_name"]["show"] = True
                build_config["new_column_value"]["show"] = True
            elif internal_operation == "Select Columns":
                build_config["columns_to_select"]["show"] = True
            elif internal_operation in {"Head", "Tail"}:
                build_config["num_rows"]["show"] = True
            elif internal_operation == "Replace Value":
                build_config["column_name"]["show"] = True
                build_config["replace_value"]["show"] = True
                build_config["replacement_value"]["show"] = True
            elif internal_operation == "Drop Duplicates":
                build_config["column_name"]["show"] = True

        return build_config

    def perform_operation(self) -> DataFrame:
        try:
            df_copy = self.df.copy()

            # Handle SortableListInput format for operation
            operation_input = getattr(self, "operation", [])
            if isinstance(operation_input, list) and len(operation_input) > 0:
                op = operation_input[0].get("name", "")
            else:
                op = ""

            # If no operation selected, return original DataFrame
            if not op:
                warning_msg = i18n.t(
                    'components.processing.dataframe_operations.warnings.no_operation_selected')
                self.status = warning_msg
                return df_copy

            # Map localized operation names to internal method names
            operation_method_map = {
                i18n.t('components.processing.dataframe_operations.operations.add_column'): "add_column",
                i18n.t('components.processing.dataframe_operations.operations.drop_column'): "drop_column",
                i18n.t('components.processing.dataframe_operations.operations.filter'): "filter_rows_by_value",
                i18n.t('components.processing.dataframe_operations.operations.head'): "head",
                i18n.t('components.processing.dataframe_operations.operations.rename_column'): "rename_column",
                i18n.t('components.processing.dataframe_operations.operations.replace_value'): "replace_values",
                i18n.t('components.processing.dataframe_operations.operations.select_columns'): "select_columns",
                i18n.t('components.processing.dataframe_operations.operations.sort'): "sort_by_column",
                i18n.t('components.processing.dataframe_operations.operations.tail'): "tail",
                i18n.t('components.processing.dataframe_operations.operations.drop_duplicates'): "drop_duplicates",
                # Also support English names for backwards compatibility
                "Add Column": "add_column",
                "Drop Column": "drop_column",
                "Filter": "filter_rows_by_value",
                "Head": "head",
                "Rename Column": "rename_column",
                "Replace Value": "replace_values",
                "Select Columns": "select_columns",
                "Sort": "sort_by_column",
                "Tail": "tail",
                "Drop Duplicates": "drop_duplicates",
            }

            method_name = operation_method_map.get(op)
            if method_name and hasattr(self, method_name):
                handler = getattr(self, method_name)
                result = handler(df_copy)

                success_msg = i18n.t('components.processing.dataframe_operations.success.operation_completed',
                                     operation=op, rows=len(result))
                self.status = success_msg
                return result
            else:
                error_msg = i18n.t('components.processing.dataframe_operations.errors.unsupported_operation',
                                   operation=op)
                self.status = error_msg
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.operation_failed',
                               error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def filter_rows_by_value(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            column = df[self.column_name]
            filter_value = self.filter_value

            # Handle regular DropdownInput format (just a string value)
            operator = getattr(self, "filter_operator", i18n.t(
                'components.processing.dataframe_operations.filter_operators.equals'))

            # Map localized operators to internal logic
            operator_map = {
                i18n.t('components.processing.dataframe_operations.filter_operators.equals'): "equals",
                i18n.t('components.processing.dataframe_operations.filter_operators.not_equals'): "not_equals",
                i18n.t('components.processing.dataframe_operations.filter_operators.contains'): "contains",
                i18n.t('components.processing.dataframe_operations.filter_operators.not_contains'): "not_contains",
                i18n.t('components.processing.dataframe_operations.filter_operators.starts_with'): "starts_with",
                i18n.t('components.processing.dataframe_operations.filter_operators.ends_with'): "ends_with",
                i18n.t('components.processing.dataframe_operations.filter_operators.greater_than'): "greater_than",
                i18n.t('components.processing.dataframe_operations.filter_operators.less_than'): "less_than",
                # Also support English for backwards compatibility
                "equals": "equals",
                "not equals": "not_equals",
                "contains": "contains",
                "not contains": "not_contains",
                "starts with": "starts_with",
                "ends with": "ends_with",
                "greater than": "greater_than",
                "less than": "less_than",
            }

            internal_operator = operator_map.get(operator, "equals")

            if internal_operator == "equals":
                mask = column == filter_value
            elif internal_operator == "not_equals":
                mask = column != filter_value
            elif internal_operator == "contains":
                mask = column.astype(str).str.contains(
                    str(filter_value), na=False)
            elif internal_operator == "not_contains":
                mask = ~column.astype(str).str.contains(
                    str(filter_value), na=False)
            elif internal_operator == "starts_with":
                mask = column.astype(str).str.startswith(
                    str(filter_value), na=False)
            elif internal_operator == "ends_with":
                mask = column.astype(str).str.endswith(
                    str(filter_value), na=False)
            elif internal_operator == "greater_than":
                try:
                    # Try to convert filter_value to numeric for comparison
                    numeric_value = pd.to_numeric(filter_value)
                    mask = column > numeric_value
                except (ValueError, TypeError):
                    # If conversion fails, compare as strings
                    mask = column.astype(str) > str(filter_value)
            elif internal_operator == "less_than":
                try:
                    # Try to convert filter_value to numeric for comparison
                    numeric_value = pd.to_numeric(filter_value)
                    mask = column < numeric_value
                except (ValueError, TypeError):
                    # If conversion fails, compare as strings
                    mask = column.astype(str) < str(filter_value)
            else:
                mask = column == filter_value  # Fallback to equals

            return DataFrame(df[mask])

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.filter_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def sort_by_column(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            return DataFrame(df.sort_values(by=self.column_name, ascending=self.ascending))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.sort_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def drop_column(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            return DataFrame(df.drop(columns=[self.column_name]))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.drop_column_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def rename_column(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            if not self.new_column_name or not self.new_column_name.strip():
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.new_column_name_required')
                raise ValueError(error_msg)

            return DataFrame(df.rename(columns={self.column_name: self.new_column_name}))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.rename_column_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def add_column(self, df: DataFrame) -> DataFrame:
        try:
            if not self.new_column_name or not self.new_column_name.strip():
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.new_column_name_required')
                raise ValueError(error_msg)

            df[self.new_column_name] = [self.new_column_value] * len(df)
            return DataFrame(df)

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.add_column_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def select_columns(self, df: DataFrame) -> DataFrame:
        try:
            if not self.columns_to_select:
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.columns_to_select_required')
                raise ValueError(error_msg)

            columns = [col.strip()
                       for col in self.columns_to_select if col.strip()]

            if not columns:
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.no_valid_columns')
                raise ValueError(error_msg)

            missing_columns = [col for col in columns if col not in df.columns]
            if missing_columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.columns_not_found',
                                   columns=', '.join(missing_columns), available=available_cols)
                raise ValueError(error_msg)

            return DataFrame(df[columns])

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.select_columns_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def head(self, df: DataFrame) -> DataFrame:
        try:
            if self.num_rows < 1:
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.invalid_num_rows')
                raise ValueError(error_msg)

            return DataFrame(df.head(self.num_rows))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.head_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def tail(self, df: DataFrame) -> DataFrame:
        try:
            if self.num_rows < 1:
                error_msg = i18n.t(
                    'components.processing.dataframe_operations.errors.invalid_num_rows')
                raise ValueError(error_msg)

            return DataFrame(df.tail(self.num_rows))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.tail_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def replace_values(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            df[self.column_name] = df[self.column_name].replace(
                self.replace_value, self.replacement_value)
            return DataFrame(df)

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.replace_values_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def drop_duplicates(self, df: DataFrame) -> DataFrame:
        try:
            if self.column_name and self.column_name not in df.columns:
                available_cols = ', '.join(df.columns)
                error_msg = i18n.t('components.processing.dataframe_operations.errors.column_not_found',
                                   column=self.column_name, available=available_cols)
                raise ValueError(error_msg)

            subset = [self.column_name] if self.column_name else None
            return DataFrame(df.drop_duplicates(subset=subset))

        except Exception as e:
            error_msg = i18n.t('components.processing.dataframe_operations.errors.drop_duplicates_failed',
                               error=str(e))
            raise ValueError(error_msg) from e
