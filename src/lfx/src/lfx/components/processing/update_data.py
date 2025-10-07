from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import (
    BoolInput,
    DataInput,
    DictInput,
    IntInput,
    MessageTextInput,
)
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict


class UpdateDataComponent(Component):
    display_name: str = i18n.t(
        'components.processing.update_data.display_name')
    description: str = i18n.t('components.processing.update_data.description')
    documentation: str = "https://docs.langflow.org/components-processing#update-data"
    name: str = "UpdateData"
    MAX_FIELDS = 15  # Define a constant for maximum number of fields
    icon = "FolderSync"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="old_data",
            display_name=i18n.t(
                'components.processing.update_data.old_data.display_name'),
            info=i18n.t('components.processing.update_data.old_data.info'),
            is_list=True,  # Changed to True to handle list of Data objects
            required=True,
        ),
        IntInput(
            name="number_of_fields",
            display_name=i18n.t(
                'components.processing.update_data.number_of_fields.display_name'),
            info=i18n.t(
                'components.processing.update_data.number_of_fields.info'),
            real_time_refresh=True,
            value=0,
            range_spec=RangeSpec(min=1, max=MAX_FIELDS,
                                 step=1, step_type="int"),
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.processing.update_data.text_key.display_name'),
            info=i18n.t('components.processing.update_data.text_key.info'),
            advanced=True,
        ),
        BoolInput(
            name="text_key_validator",
            display_name=i18n.t(
                'components.processing.update_data.text_key_validator.display_name'),
            info=i18n.t(
                'components.processing.update_data.text_key_validator.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.update_data.outputs.data.display_name'),
            name="data",
            method="build_data"
        ),
    ]

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        """Update the build configuration when the number of fields changes."""
        try:
            if field_name == "number_of_fields":
                default_keys = {
                    "code",
                    "_type",
                    "number_of_fields",
                    "text_key",
                    "old_data",
                    "text_key_validator",
                }

                # Validate field value
                try:
                    field_value_int = int(field_value)
                except (ValueError, TypeError):
                    error_msg = i18n.t('components.processing.update_data.errors.invalid_number_of_fields',
                                       value=field_value)
                    self.log(error_msg, "warning")
                    return build_config

                # Check maximum fields limit
                if field_value_int > self.MAX_FIELDS:
                    build_config["number_of_fields"]["value"] = self.MAX_FIELDS
                    error_msg = i18n.t('components.processing.update_data.errors.too_many_fields',
                                       max_fields=self.MAX_FIELDS)
                    raise ValueError(error_msg)

                # Back up existing template fields
                existing_fields = {}
                for key in list(build_config.keys()):
                    if key not in default_keys:
                        existing_fields[key] = build_config.pop(key)

                # Create or restore field inputs
                for i in range(1, field_value_int + 1):
                    key = f"field_{i}_key"
                    if key in existing_fields:
                        field = existing_fields[key]
                        build_config[key] = field
                    else:
                        field = DictInput(
                            display_name=i18n.t('components.processing.update_data.dynamic_field.display_name',
                                                number=i),
                            name=key,
                            info=i18n.t(
                                'components.processing.update_data.dynamic_field.info', number=i),
                            input_types=["Message", "Data"],
                        )
                        build_config[field.name] = field.to_dict()

                build_config["number_of_fields"]["value"] = field_value_int

            return build_config

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.build_config_update_failed', error=str(e))
            self.log(error_msg, "error")
            return build_config

    async def build_data(self) -> Data | list[Data]:
        """Build the updated data by combining the old data with new fields."""
        try:
            # Validate old_data
            if not hasattr(self, 'old_data') or not self.old_data:
                error_msg = i18n.t(
                    'components.processing.update_data.errors.no_old_data')
                self.status = error_msg
                raise ValueError(error_msg)

            # Get new data to be added
            try:
                new_data = self.get_data()
            except Exception as e:
                error_msg = i18n.t(
                    'components.processing.update_data.errors.get_data_failed', error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Process based on input type
            if isinstance(self.old_data, list):
                return await self._process_data_list(new_data)
            elif isinstance(self.old_data, Data):
                return await self._process_single_data(new_data)
            else:
                error_msg = i18n.t('components.processing.update_data.errors.invalid_old_data_type',
                                   actual_type=type(self.old_data).__name__)
                self.status = error_msg
                raise ValueError(error_msg)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.build_data_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    async def _process_data_list(self, new_data: dict) -> list[Data]:
        """Process a list of Data objects."""
        try:
            updated_count = 0
            skipped_count = 0

            for i, data_item in enumerate(self.old_data):
                if not isinstance(data_item, Data):
                    skipped_count += 1
                    warning_msg = i18n.t('components.processing.update_data.warnings.invalid_list_item',
                                         index=i, actual_type=type(data_item).__name__)
                    self.log(warning_msg, "warning")
                    continue  # Skip invalid items

                # Update data
                try:
                    data_item.data.update(new_data)
                    if self.text_key:
                        data_item.text_key = self.text_key
                    self.validate_text_key(data_item)
                    updated_count += 1
                except Exception as e:
                    skipped_count += 1
                    error_msg = i18n.t('components.processing.update_data.errors.list_item_update_failed',
                                       index=i, error=str(e))
                    self.log(error_msg, "warning")
                    continue

            # Set status with results
            if updated_count == 0:
                warning_msg = i18n.t(
                    'components.processing.update_data.warnings.no_items_updated')
                self.status = warning_msg
            elif skipped_count > 0:
                status_msg = i18n.t('components.processing.update_data.success.partial_list_update',
                                    updated=updated_count, skipped=skipped_count, total=len(self.old_data))
                self.status = status_msg
            else:
                success_msg = i18n.t('components.processing.update_data.success.full_list_update',
                                     count=updated_count)
                self.status = success_msg

            return self.old_data  # Returns List[Data]

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.list_processing_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    async def _process_single_data(self, new_data: dict) -> Data:
        """Process a single Data object."""
        try:
            self.old_data.data.update(new_data)
            if self.text_key:
                self.old_data.text_key = self.text_key
            self.validate_text_key(self.old_data)

            success_msg = i18n.t('components.processing.update_data.success.single_data_update',
                                 fields_added=len(new_data))
            self.status = success_msg

            return self.old_data  # Returns Data

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.single_data_update_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def get_data(self) -> dict:
        """Function to get the Data from the attributes."""
        try:
            data = {}
            default_keys = {
                "code",
                "_type",
                "number_of_fields",
                "text_key",
                "old_data",
                "text_key_validator",
            }

            processed_fields = 0
            for attr_name, attr_value in self._attributes.items():
                if attr_name in default_keys:
                    continue  # Skip default attributes

                try:
                    if isinstance(attr_value, dict):
                        for key, value in attr_value.items():
                            data[key] = value.get_text() if isinstance(
                                value, Data) else value
                            processed_fields += 1
                    elif isinstance(attr_value, Data):
                        data[attr_name] = attr_value.get_text()
                        processed_fields += 1
                    else:
                        data[attr_name] = attr_value
                        processed_fields += 1
                except Exception as e:
                    warning_msg = i18n.t('components.processing.update_data.warnings.field_processing_failed',
                                         field=attr_name, error=str(e))
                    self.log(warning_msg, "warning")
                    continue

            self.log(i18n.t('components.processing.update_data.logs.data_extracted',
                            fields=processed_fields))
            return data

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.data_extraction_failed', error=str(e))
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def validate_text_key(self, data: Data) -> None:
        """This function validates that the Text Key is one of the keys in the Data."""
        try:
            if not self.text_key_validator:
                return  # Skip validation if not enabled

            if not self.text_key:
                return  # No text key to validate

            data_keys = list(data.data.keys()) if data.data else []

            if self.text_key not in data_keys:
                error_msg = i18n.t('components.processing.update_data.errors.text_key_not_found',
                                   text_key=self.text_key, available_keys=', '.join(data_keys))
                raise ValueError(error_msg)

            # Log successful validation
            self.log(i18n.t('components.processing.update_data.logs.text_key_validated',
                            text_key=self.text_key))

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.update_data.errors.text_key_validation_failed', error=str(e))
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e
