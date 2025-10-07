import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataFrameInput, MultilineInput, Output, StrInput
from lfx.schema.message import Message


class ParseDataFrameComponent(Component):
    display_name = i18n.t('components.processing.parse_dataframe.display_name')
    description = i18n.t('components.processing.parse_dataframe.description')
    icon = "braces"
    name = "ParseDataFrame"
    legacy = True
    replacement = ["processing.DataFrameOperations",
                   "processing.TypeConverterComponent"]

    inputs = [
        DataFrameInput(
            name="df",
            display_name=i18n.t(
                'components.processing.parse_dataframe.df.display_name'),
            info=i18n.t('components.processing.parse_dataframe.df.info')
        ),
        MultilineInput(
            name="template",
            display_name=i18n.t(
                'components.processing.parse_dataframe.template.display_name'),
            info=i18n.t('components.processing.parse_dataframe.template.info'),
            value="{text}",
        ),
        StrInput(
            name="sep",
            display_name=i18n.t(
                'components.processing.parse_dataframe.sep.display_name'),
            advanced=True,
            value="\n",
            info=i18n.t('components.processing.parse_dataframe.sep.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.parse_dataframe.outputs.text.display_name'),
            name="text",
            info=i18n.t(
                'components.processing.parse_dataframe.outputs.text.info'),
            method="parse_data",
        ),
    ]

    def _clean_args(self):
        """Clean and validate input arguments."""
        try:
            dataframe = self.df
            template = self.template or "{text}"
            sep = self.sep if self.sep is not None else "\n"

            # Validate DataFrame
            if dataframe is None or dataframe.empty:
                error_msg = i18n.t(
                    'components.processing.parse_dataframe.errors.empty_dataframe')
                self.status = error_msg
                raise ValueError(error_msg)

            # Validate template
            if not template or not template.strip():
                error_msg = i18n.t(
                    'components.processing.parse_dataframe.errors.empty_template')
                self.status = error_msg
                raise ValueError(error_msg)

            return dataframe, template, sep

        except Exception as e:
            error_msg = i18n.t('components.processing.parse_dataframe.errors.argument_validation_failed',
                               error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def parse_data(self) -> Message:
        """Converts each row of the DataFrame into a formatted string using the template,
        then joins them with `sep`. Returns a single combined string as a Message.
        """
        try:
            dataframe, template, sep = self._clean_args()

            lines = []
            missing_columns = set()
            successful_rows = 0

            # For each row in the DataFrame, build a dict and format
            for row_index, row in dataframe.iterrows():
                try:
                    row_dict = row.to_dict()

                    # Try to format the template with the row data
                    text_line = template.format(**row_dict)
                    lines.append(text_line)
                    successful_rows += 1

                except KeyError as e:
                    # Track missing columns for better error reporting
                    missing_key = str(e).strip("'\"")
                    missing_columns.add(missing_key)

                    # Use a fallback - add the row as is or skip
                    warning_msg = i18n.t('components.processing.parse_dataframe.warnings.missing_column_in_row',
                                         row=row_index, column=missing_key)
                    self.log(warning_msg, "warning")

                except Exception as e:
                    # Handle other formatting errors
                    error_msg = i18n.t('components.processing.parse_dataframe.errors.row_formatting_failed',
                                       row=row_index, error=str(e))
                    self.log(error_msg, "warning")

            # Check if we have missing columns
            if missing_columns:
                available_columns = list(dataframe.columns)
                warning_msg = i18n.t('components.processing.parse_dataframe.warnings.missing_columns',
                                     missing=', '.join(
                                         sorted(missing_columns)),
                                     available=', '.join(available_columns))
                self.log(warning_msg, "warning")

            # Join all lines with the provided separator
            result_string = sep.join(lines)

            # Set status based on results
            if successful_rows == 0:
                error_msg = i18n.t(
                    'components.processing.parse_dataframe.errors.no_successful_rows')
                self.status = error_msg
                raise ValueError(error_msg)
            elif successful_rows < len(dataframe):
                warning_msg = i18n.t('components.processing.parse_dataframe.warnings.partial_success',
                                     successful=successful_rows, total=len(dataframe))
                self.status = warning_msg
            else:
                success_msg = i18n.t('components.processing.parse_dataframe.success.all_rows_processed',
                                     rows=successful_rows, length=len(result_string))
                self.status = success_msg

            return Message(text=result_string)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_dataframe.errors.parsing_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
