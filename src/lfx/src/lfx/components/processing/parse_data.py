import i18n

from lfx.custom.custom_component.component import Component
from lfx.helpers.data import data_to_text, data_to_text_list
from lfx.io import DataInput, MultilineInput, Output, StrInput
from lfx.schema.data import Data
from lfx.schema.message import Message


class ParseDataComponent(Component):
    display_name = i18n.t('components.processing.parse_data.display_name')
    description = i18n.t('components.processing.parse_data.description')
    icon = "message-square"
    name = "ParseData"
    legacy = True
    replacement = ["processing.DataOperations",
                   "processing.TypeConverterComponent"]
    metadata = {
        "legacy_name": "Parse Data",
    }

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t(
                'components.processing.parse_data.data.display_name'),
            info=i18n.t('components.processing.parse_data.data.info'),
            is_list=True,
            required=True,
        ),
        MultilineInput(
            name="template",
            display_name=i18n.t(
                'components.processing.parse_data.template.display_name'),
            info=i18n.t('components.processing.parse_data.template.info'),
            value="{text}",
            required=True,
        ),
        StrInput(
            name="sep",
            display_name=i18n.t(
                'components.processing.parse_data.sep.display_name'),
            info=i18n.t('components.processing.parse_data.sep.info'),
            advanced=True,
            value="\n"
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.parse_data.outputs.message.display_name'),
            name="text",
            info=i18n.t(
                'components.processing.parse_data.outputs.message.info'),
            method="parse_data",
        ),
        Output(
            display_name=i18n.t(
                'components.processing.parse_data.outputs.data_list.display_name'),
            name="data_list",
            info=i18n.t(
                'components.processing.parse_data.outputs.data_list.info'),
            method="parse_data_as_list",
        ),
    ]

    def _clean_args(self) -> tuple[list[Data], str, str]:
        """Clean and validate input arguments."""
        try:
            data = self.data if isinstance(self.data, list) else [self.data]

            # Validate data
            if not data or all(item is None for item in data):
                error_msg = i18n.t(
                    'components.processing.parse_data.errors.empty_data')
                self.status = error_msg
                raise ValueError(error_msg)

            # Filter out None values
            data = [item for item in data if item is not None]

            template = self.template if self.template else "{text}"
            sep = self.sep if self.sep is not None else "\n"

            return data, template, sep

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_data.errors.argument_validation_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def parse_data(self) -> Message:
        """Convert Data objects to a single Message using the template and separator."""
        try:
            data, template, sep = self._clean_args()

            if not data:
                warning_msg = i18n.t(
                    'components.processing.parse_data.warnings.no_valid_data')
                self.status = warning_msg
                return Message(text="")

            result_string = data_to_text(template, data, sep)

            if not result_string:
                warning_msg = i18n.t(
                    'components.processing.parse_data.warnings.empty_result')
                self.status = warning_msg
                return Message(text="")

            success_msg = i18n.t('components.processing.parse_data.success.data_parsed_to_message',
                                 count=len(data), length=len(result_string))
            self.status = success_msg

            return Message(text=result_string)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_data.errors.parse_to_message_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def parse_data_as_list(self) -> list[Data]:
        """Convert Data objects to a list of new Data objects with formatted text."""
        try:
            data, template, _ = self._clean_args()

            if not data:
                warning_msg = i18n.t(
                    'components.processing.parse_data.warnings.no_valid_data')
                self.status = warning_msg
                return []

            text_list, data_list = data_to_text_list(template, data)

            # Set the formatted text on each Data object
            for item, text in zip(data_list, text_list, strict=True):
                item.set_text(text)

            success_msg = i18n.t('components.processing.parse_data.success.data_parsed_to_list',
                                 count=len(data_list))
            self.status = success_msg

            return data_list

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parse_data.errors.parse_to_list_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
