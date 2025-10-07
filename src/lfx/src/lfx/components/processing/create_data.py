from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput, DictInput, IntInput, MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict


class CreateDataComponent(Component):
    display_name: str = i18n.t(
        'components.processing.create_data.display_name')
    description: str = i18n.t('components.processing.create_data.description')
    name: str = "CreateData"
    MAX_FIELDS = 15  # Define a constant for maximum number of fields
    legacy = True
    replacement = ["processing.DataOperations"]
    icon = "ListFilter"

    inputs = [
        IntInput(
            name="number_of_fields",
            display_name=i18n.t(
                'components.processing.create_data.number_of_fields.display_name'),
            info=i18n.t(
                'components.processing.create_data.number_of_fields.info'),
            real_time_refresh=True,
            value=1,
            range_spec=RangeSpec(min=1, max=MAX_FIELDS,
                                 step=1, step_type="int"),
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.processing.create_data.text_key.display_name'),
            info=i18n.t('components.processing.create_data.text_key.info'),
            advanced=True,
        ),
        BoolInput(
            name="text_key_validator",
            display_name=i18n.t(
                'components.processing.create_data.text_key_validator.display_name'),
            advanced=True,
            info=i18n.t(
                'components.processing.create_data.text_key_validator.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.create_data.outputs.data.display_name'),
            name="data",
            method="build_data"
        ),
    ]

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        if field_name == "number_of_fields":
            default_keys = ["code", "_type", "number_of_fields",
                            "text_key", "text_key_validator"]
            try:
                field_value_int = int(field_value)
            except ValueError:
                error_msg = i18n.t(
                    'components.processing.create_data.errors.invalid_field_count')
                self.status = error_msg
                return build_config

            existing_fields = {}

            if field_value_int > self.MAX_FIELDS:
                build_config["number_of_fields"]["value"] = self.MAX_FIELDS
                error_msg = i18n.t('components.processing.create_data.errors.max_fields_exceeded',
                                   max_fields=self.MAX_FIELDS)
                raise ValueError(error_msg)

            if len(build_config) > len(default_keys):
                # back up the existing template fields
                for key in build_config.copy():
                    if key not in default_keys:
                        existing_fields[key] = build_config.pop(key)

            for i in range(1, field_value_int + 1):
                key = f"field_{i}_key"
                if key in existing_fields:
                    field = existing_fields[key]
                    build_config[key] = field
                else:
                    field_display_name = i18n.t(
                        'components.processing.create_data.field.display_name', number=i)
                    field_info = i18n.t(
                        'components.processing.create_data.field.info', number=i)

                    field = DictInput(
                        display_name=field_display_name,
                        name=key,
                        info=field_info,
                        input_types=["Message", "Data"],
                    )
                    build_config[field.name] = field.to_dict()

            build_config["number_of_fields"]["value"] = field_value_int

            success_msg = i18n.t('components.processing.create_data.success.fields_configured',
                                 count=field_value_int)
            self.status = success_msg

        return build_config

    async def build_data(self) -> Data:
        try:
            data = self.get_data()
            return_data = Data(data=data, text_key=self.text_key)

            if self.text_key_validator:
                self.validate_text_key()

            field_count = len(data)
            success_msg = i18n.t('components.processing.create_data.success.data_created',
                                 count=field_count)
            self.status = success_msg

            return return_data

        except ValueError:
            # Re-raise ValueError as is (already has i18n message from validate_text_key)
            raise
        except Exception as e:
            error_msg = i18n.t('components.processing.create_data.errors.data_creation_failed',
                               error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def get_data(self):
        """Function to get the Data from the attributes."""
        try:
            data = {}
            for value_dict in self._attributes.values():
                if isinstance(value_dict, dict):
                    # Check if the value of the value_dict is a Data
                    value_dict_ = {
                        key: value.get_text() if isinstance(value, Data) else value
                        for key, value in value_dict.items()
                    }
                    data.update(value_dict_)
            return data

        except Exception as e:
            error_msg = i18n.t('components.processing.create_data.errors.data_extraction_failed',
                               error=str(e))
            raise ValueError(error_msg) from e

    def validate_text_key(self) -> None:
        """This function validates that the Text Key is one of the keys in the Data."""
        try:
            data_keys = self.get_data().keys()

            if self.text_key and self.text_key not in data_keys:
                formatted_data_keys = ", ".join(data_keys)
                error_msg = i18n.t('components.processing.create_data.errors.text_key_not_found',
                                   text_key=self.text_key, data_keys=formatted_data_keys)
                raise ValueError(error_msg)

            if self.text_key:
                success_msg = i18n.t('components.processing.create_data.success.text_key_validated',
                                     text_key=self.text_key)
                self.log(success_msg)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t('components.processing.create_data.errors.text_key_validation_failed',
                               error=str(e))
            raise ValueError(error_msg) from e
