import csv
import io
from pathlib import Path
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data


class CSVToDataComponent(Component):
    display_name = i18n.t('components.data.csv_to_data.display_name')
    description = i18n.t('components.data.csv_to_data.description')
    icon = "file-spreadsheet"
    name = "CSVtoData"
    legacy = True
    replacement = ["data.File"]

    inputs = [
        FileInput(
            name="csv_file",
            display_name=i18n.t(
                'components.data.csv_to_data.csv_file.display_name'),
            file_types=["csv"],
            info=i18n.t('components.data.csv_to_data.csv_file.info'),
        ),
        MessageTextInput(
            name="csv_path",
            display_name=i18n.t(
                'components.data.csv_to_data.csv_path.display_name'),
            info=i18n.t('components.data.csv_to_data.csv_path.info'),
        ),
        MultilineInput(
            name="csv_string",
            display_name=i18n.t(
                'components.data.csv_to_data.csv_string.display_name'),
            info=i18n.t('components.data.csv_to_data.csv_string.info'),
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.csv_to_data.text_key.display_name'),
            info=i18n.t('components.data.csv_to_data.text_key.info'),
            value="text",
        ),
    ]

    outputs = [
        Output(name="data_list", display_name=i18n.t(
            'components.data.csv_to_data.outputs.data_list.display_name'), method="load_csv_to_data"),
    ]

    def load_csv_to_data(self) -> list[Data]:
        if sum(bool(field) for field in [self.csv_file, self.csv_path, self.csv_string]) != 1:
            msg = i18n.t(
                'components.data.csv_to_data.errors.exactly_one_input')
            raise ValueError(msg)

        csv_data = None
        try:
            if self.csv_file:
                resolved_path = self.resolve_path(self.csv_file)
                file_path = Path(resolved_path)
                if file_path.suffix.lower() != ".csv":
                    self.status = i18n.t(
                        'components.data.csv_to_data.errors.must_be_csv')
                else:
                    with file_path.open(newline="", encoding="utf-8") as csvfile:
                        csv_data = csvfile.read()

            elif self.csv_path:
                file_path = Path(self.csv_path)
                if file_path.suffix.lower() != ".csv":
                    self.status = i18n.t(
                        'components.data.csv_to_data.errors.must_be_csv')
                else:
                    with file_path.open(newline="", encoding="utf-8") as csvfile:
                        csv_data = csvfile.read()

            else:
                csv_data = self.csv_string

            if csv_data:
                csv_reader = csv.DictReader(io.StringIO(csv_data))
                result = [Data(data=row, text_key=self.text_key)
                          for row in csv_reader]

                if not result:
                    self.status = i18n.t(
                        'components.data.csv_to_data.errors.empty_csv')
                    return []

                self.status = result
                return result

        except csv.Error as e:
            error_message = i18n.t(
                'components.data.csv_to_data.errors.csv_parsing_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

        except Exception as e:
            error_message = i18n.t(
                'components.data.csv_to_data.errors.generic_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

        # An error occurred
        raise ValueError(self.status)
