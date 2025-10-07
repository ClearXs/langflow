import json
from pathlib import Path
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data


class JSONToDataComponent(Component):
    display_name = i18n.t('components.data.json_to_data.display_name')
    description = i18n.t('components.data.json_to_data.description')
    icon = "braces"
    name = "JSONtoData"
    legacy = True
    replacement = ["data.File"]

    inputs = [
        FileInput(
            name="json_file",
            display_name=i18n.t(
                'components.data.json_to_data.json_file.display_name'),
            file_types=["json"],
            info=i18n.t('components.data.json_to_data.json_file.info'),
        ),
        MessageTextInput(
            name="json_path",
            display_name=i18n.t(
                'components.data.json_to_data.json_path.display_name'),
            info=i18n.t('components.data.json_to_data.json_path.info'),
        ),
        MultilineInput(
            name="json_string",
            display_name=i18n.t(
                'components.data.json_to_data.json_string.display_name'),
            info=i18n.t('components.data.json_to_data.json_string.info'),
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.json_to_data.text_key.display_name'),
            info=i18n.t('components.data.json_to_data.text_key.info'),
            value="text",
        ),
    ]

    outputs = [
        Output(
            name="data_list",
            display_name=i18n.t(
                'components.data.json_to_data.outputs.data_list.display_name'),
            method="load_json_to_data"
        ),
    ]

    def load_json_to_data(self) -> list[Data]:
        if sum(bool(field) for field in [self.json_file, self.json_path, self.json_string]) != 1:
            msg = i18n.t(
                'components.data.json_to_data.errors.exactly_one_input')
            raise ValueError(msg)

        json_data = None
        try:
            if self.json_file:
                resolved_path = self.resolve_path(self.json_file)
                file_path = Path(resolved_path)
                if file_path.suffix.lower() != ".json":
                    self.status = i18n.t(
                        'components.data.json_to_data.errors.must_be_json')
                    raise ValueError(self.status)
                else:
                    with file_path.open(encoding="utf-8") as jsonfile:
                        json_data = json.load(jsonfile)

            elif self.json_path:
                file_path = Path(self.json_path)
                if file_path.suffix.lower() != ".json":
                    self.status = i18n.t(
                        'components.data.json_to_data.errors.must_be_json')
                    raise ValueError(self.status)
                else:
                    with file_path.open(encoding="utf-8") as jsonfile:
                        json_data = json.load(jsonfile)

            else:
                json_data = json.loads(self.json_string)

            if json_data is not None:
                # Handle both single objects and arrays
                if isinstance(json_data, list):
                    result = [Data(data=item, text_key=self.text_key)
                              for item in json_data]
                else:
                    result = [Data(data=json_data, text_key=self.text_key)]

                if not result:
                    self.status = i18n.t(
                        'components.data.json_to_data.errors.empty_json')
                    return []

                self.status = result
                return result

        except json.JSONDecodeError as e:
            error_message = i18n.t(
                'components.data.json_to_data.errors.json_parsing_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

        except Exception as e:
            error_message = i18n.t(
                'components.data.json_to_data.errors.generic_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

        # An error occurred
        raise ValueError(self.status)
