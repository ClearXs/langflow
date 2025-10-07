import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import DataInput, IntInput
from lfx.io import Output
from lfx.schema.data import Data


class SelectDataComponent(Component):
    display_name: str = i18n.t(
        'components.processing.select_data.display_name')
    description: str = i18n.t('components.processing.select_data.description')
    name: str = "SelectData"
    icon = "prototypes"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="data_list",
            display_name=i18n.t(
                'components.processing.select_data.data_list.display_name'),
            info=i18n.t('components.processing.select_data.data_list.info'),
            is_list=True,  # Specify that this input takes a list of Data objects
            required=True,
        ),
        IntInput(
            name="data_index",
            display_name=i18n.t(
                'components.processing.select_data.data_index.display_name'),
            info=i18n.t('components.processing.select_data.data_index.info'),
            value=0,  # Will be populated dynamically based on the length of data_list
            range_spec=RangeSpec(min=0, max=15, step=1, step_type="int"),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.select_data.outputs.selected_data.display_name'),
            name="selected_data",
            method="select_data"
        ),
    ]

    async def select_data(self) -> Data:
        """Select a single Data object from the list based on the specified index."""
        try:
            # Validate data list
            if not hasattr(self, 'data_list') or not self.data_list:
                error_msg = i18n.t(
                    'components.processing.select_data.errors.empty_data_list')
                self.status = error_msg
                raise ValueError(error_msg)

            if not isinstance(self.data_list, list):
                error_msg = i18n.t(
                    'components.processing.select_data.errors.invalid_data_list_type')
                self.status = error_msg
                raise ValueError(error_msg)

            # Validate index
            if not hasattr(self, 'data_index'):
                error_msg = i18n.t(
                    'components.processing.select_data.errors.missing_data_index')
                self.status = error_msg
                raise ValueError(error_msg)

            try:
                selected_index = int(self.data_index)
            except (TypeError, ValueError) as e:
                error_msg = i18n.t('components.processing.select_data.errors.invalid_index_type',
                                   index=self.data_index, error=str(e))
                self.status = error_msg
                raise ValueError(error_msg) from e

            # Validate that the selected index is within bounds
            data_list_length = len(self.data_list)
            if selected_index < 0:
                error_msg = i18n.t('components.processing.select_data.errors.negative_index',
                                   index=selected_index)
                self.status = error_msg
                raise ValueError(error_msg)

            if selected_index >= data_list_length:
                error_msg = i18n.t('components.processing.select_data.errors.index_out_of_range',
                                   index=selected_index, max_index=data_list_length - 1, length=data_list_length)
                self.status = error_msg
                raise ValueError(error_msg)

            # Return the selected Data object
            selected_data = self.data_list[selected_index]

            # Validate that the selected item is a Data object
            if not isinstance(selected_data, Data):
                error_msg = i18n.t('components.processing.select_data.errors.invalid_selected_data_type',
                                   index=selected_index, actual_type=type(selected_data).__name__)
                self.status = error_msg
                raise ValueError(error_msg)

            # Update status with success message
            success_msg = i18n.t('components.processing.select_data.success.data_selected',
                                 index=selected_index, total=data_list_length)
            self.status = success_msg

            # Log the selection
            self.log(i18n.t('components.processing.select_data.logs.data_selected',
                            index=selected_index, data_preview=str(selected_data)[:100]))

            return selected_data

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.select_data.errors.selection_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def update_build_config(self, build_config, field_value, field_name=None):
        """Update the range_spec max value based on data_list length."""
        try:
            if field_name == "data_list" and field_value:
                data_list_length = len(field_value) if isinstance(
                    field_value, list) else 1
                max_index = max(0, data_list_length - 1)

                # Update the range_spec for data_index
                build_config["data_index"]["range_spec"] = RangeSpec(
                    min=0,
                    max=max_index,
                    step=1,
                    step_type="int"
                ).to_dict()

                # Also update the info text to show available range
                if data_list_length > 0:
                    build_config["data_index"]["info"] = i18n.t(
                        'components.processing.select_data.data_index.info_with_range',
                        max_index=max_index, length=data_list_length
                    )
                else:
                    build_config["data_index"]["info"] = i18n.t(
                        'components.processing.select_data.data_index.info_empty_list'
                    )

            return build_config

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.select_data.errors.build_config_update_failed', error=str(e))
            self.log(error_msg, "warning")
            return build_config
