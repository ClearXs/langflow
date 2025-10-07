import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class DataToDataFrameComponent(Component):
    display_name = i18n.t(
        'components.processing.data_to_dataframe.display_name')
    description = i18n.t('components.processing.data_to_dataframe.description')
    icon = "table"
    name = "DataToDataFrame"
    legacy = True
    replacement = ["processing.DataOperations",
                   "processing.TypeConverterComponent"]

    inputs = [
        DataInput(
            name="data_list",
            display_name=i18n.t(
                'components.processing.data_to_dataframe.data_list.display_name'),
            info=i18n.t(
                'components.processing.data_to_dataframe.data_list.info'),
            is_list=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.data_to_dataframe.outputs.dataframe.display_name'),
            name="dataframe",
            method="build_dataframe",
            info=i18n.t(
                'components.processing.data_to_dataframe.outputs.dataframe.info'),
        ),
    ]

    def build_dataframe(self) -> DataFrame:
        """Builds a DataFrame from Data objects by combining their fields.

        For each Data object:
          - Merge item.data (dictionary) as columns
          - If item.text is present, add 'text' column

        Returns a DataFrame with one row per Data object.
        """
        try:
            data_input = self.data_list

            # Validate input
            if not data_input:
                warning_msg = i18n.t(
                    'components.processing.data_to_dataframe.warnings.empty_data_list')
                self.status = warning_msg
                return DataFrame([])

            # If user passed a single Data, it might come in as a single object rather than a list
            if not isinstance(data_input, list):
                data_input = [data_input]

            rows = []
            processed_count = 0

            for idx, item in enumerate(data_input):
                if not isinstance(item, Data):
                    error_msg = i18n.t('components.processing.data_to_dataframe.errors.invalid_data_type',
                                       index=idx, actual_type=type(item).__name__)
                    self.status = error_msg
                    raise TypeError(error_msg)

                # Start with a copy of item.data or an empty dict
                row_dict = dict(item.data) if item.data else {}

                # If the Data object has text, store it under 'text' col
                text_val = item.get_text()
                if text_val:
                    row_dict["text"] = text_val

                rows.append(row_dict)
                processed_count += 1

            # Build a DataFrame from these row dictionaries
            df_result = DataFrame(rows)

            success_msg = i18n.t('components.processing.data_to_dataframe.success.dataframe_created',
                                 rows=len(rows), objects=processed_count)
            self.status = success_msg

            return df_result

        except TypeError:
            # Re-raise TypeError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t('components.processing.data_to_dataframe.errors.dataframe_creation_failed',
                               error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
