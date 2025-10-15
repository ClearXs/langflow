from typing import Any
import i18n
import pandas as pd

from lfx.custom.custom_component.component import Component
from lfx.io import (
    DataInput,
    TableInput,
    BoolInput,
    Output
)
from lfx.schema import Data


class ETLGroupByComponent(Component):
    display_name = i18n.t('components.operations.group_by.display_name')
    description = i18n.t('components.operations.group_by.description')
    icon = "layers"
    name = "ETLGroupBy"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t('components.operations.group_by.data_input.display_name'),
            info=i18n.t('components.operations.group_by.data_input.info'),
            is_list=True,
            required=True
        ),
        TableInput(
            name="group_by_columns",
            display_name=i18n.t('components.operations.group_by.group_by_columns.display_name'),
            info=i18n.t('components.operations.group_by.group_by_columns.info'),
            table_schema=[
                {"name": "column", "display_name": "Column Name", "type": "str"}
            ],
            value=[],
            required=True
        ),
        TableInput(
            name="aggregations",
            display_name=i18n.t('components.operations.group_by.aggregations.display_name'),
            info=i18n.t('components.operations.group_by.aggregations.info'),
            table_schema=[
                {"name": "column", "display_name": "Column", "type": "str"},
                {"name": "function", "display_name": "Function", "type": "str"},
                {"name": "alias", "display_name": "Alias", "type": "str"}
            ],
            value=[],
            required=True
        ),
        BoolInput(
            name="drop_na",
            display_name=i18n.t('components.operations.group_by.drop_na.display_name'),
            info=i18n.t('components.operations.group_by.drop_na.info'),
            value=True,
            advanced=True
        ),
        BoolInput(
            name="sort_results",
            display_name=i18n.t('components.operations.group_by.sort_results.display_name'),
            info=i18n.t('components.operations.group_by.sort_results.info'),
            value=False,
            advanced=True
        )
    ]

    outputs = [
        Output(name="data", display_name="Grouped Data", method="group_data"),
        Output(name="group_stats", display_name="Group Statistics", method="get_group_stats")
    ]

    def group_data(self) -> list[Data]:
        """Group data with aggregations (sum/count/avg/min/max)."""
        try:
            self.status = i18n.t('components.operations.group_by.status.grouping')

            # Validate inputs
            if not self.data_input:
                raise ValueError(i18n.t('components.operations.group_by.errors.no_data'))

            if not self.group_by_columns:
                raise ValueError(i18n.t('components.operations.group_by.errors.no_group_columns'))

            if not self.aggregations:
                raise ValueError(i18n.t('components.operations.group_by.errors.no_aggregations'))

            # Convert to DataFrame
            df = self._convert_to_dataframe(self.data_input)

            # Extract group by columns
            group_cols = [col['column'] for col in self.group_by_columns]

            # Build aggregation dictionary
            agg_dict = {}
            alias_mapping = {}

            for agg in self.aggregations:
                column = agg['column']
                function = agg['function'].lower()
                alias = agg.get('alias', f"{column}_{function}")

                # Map function names
                func_mapping = {
                    'sum': 'sum',
                    'count': 'count',
                    'avg': 'mean',
                    'mean': 'mean',
                    'min': 'min',
                    'max': 'max',
                    'std': 'std',
                    'median': 'median',
                    'first': 'first',
                    'last': 'last'
                }

                pandas_func = func_mapping.get(function, 'sum')

                if column not in agg_dict:
                    agg_dict[column] = []

                agg_dict[column].append(pandas_func)
                alias_mapping[(column, pandas_func)] = alias

            # Perform grouping
            grouped_df = df.groupby(group_cols, dropna=self.drop_na).agg(agg_dict).reset_index()

            # Flatten column names and apply aliases
            if isinstance(grouped_df.columns, pd.MultiIndex):
                new_cols = []
                for col in grouped_df.columns:
                    if col[1]:  # If there's an aggregation function
                        alias = alias_mapping.get((col[0], col[1]), f"{col[0]}_{col[1]}")
                        new_cols.append(alias)
                    else:
                        new_cols.append(col[0])
                grouped_df.columns = new_cols

            # Sort if requested
            if self.sort_results and group_cols:
                grouped_df = grouped_df.sort_values(by=group_cols)

            # Convert back to Data objects
            result_data = []
            for _, row in grouped_df.iterrows():
                row_dict = row.to_dict()
                result_data.append(Data(data=row_dict))

            self.status = i18n.t('components.operations.group_by.status.success', groups=len(result_data))
            return result_data

        except Exception as e:
            error_msg = i18n.t('components.operations.group_by.errors.group_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _convert_to_dataframe(self, data_list: list[Data]) -> pd.DataFrame:
        """Convert list of Data objects to pandas DataFrame."""
        records = []
        for data_obj in data_list:
            if hasattr(data_obj, 'data') and isinstance(data_obj.data, dict):
                records.append(data_obj.data)
            elif isinstance(data_obj, dict):
                records.append(data_obj)

        return pd.DataFrame(records)

    def get_group_stats(self) -> Data:
        """Get statistics about the grouping operation."""
        grouped = self.group_data()

        stats = {
            "group_by_columns": [col['column'] for col in self.group_by_columns],
            "aggregations": [f"{agg['column']}_{agg['function']}" for agg in self.aggregations],
            "total_groups": len(grouped),
            "input_records": len(self.data_input) if self.data_input else 0
        }

        return Data(data=stats)
