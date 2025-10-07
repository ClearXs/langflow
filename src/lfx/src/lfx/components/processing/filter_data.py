import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


class FilterDataComponent(Component):
    display_name = i18n.t('components.processing.filter_data.display_name')
    description = i18n.t('components.processing.filter_data.description')
    icon = "filter"
    beta = True
    name = "FilterData"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t(
                'components.processing.filter_data.data.display_name'),
            info=i18n.t('components.processing.filter_data.data.info'),
        ),
        MessageTextInput(
            name="filter_criteria",
            display_name=i18n.t(
                'components.processing.filter_data.filter_criteria.display_name'),
            info=i18n.t(
                'components.processing.filter_data.filter_criteria.info'),
            is_list=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.filter_data.outputs.filtered_data.display_name'),
            name="filtered_data",
            method="filter_data"
        ),
    ]

    def filter_data(self) -> Data:
        try:
            filter_criteria: list[str] = self.filter_criteria or []

            # Validate input
            if not isinstance(self.data, Data):
                error_msg = i18n.t('components.processing.filter_data.errors.invalid_data_type',
                                   actual_type=type(self.data).__name__)
                self.status = error_msg
                return Data(data={"error": error_msg})

            data = self.data.data if self.data.data else {}

            # Validate filter criteria
            if not filter_criteria:
                warning_msg = i18n.t(
                    'components.processing.filter_data.warnings.empty_filter_criteria')
                self.status = warning_msg
                return Data(data={})

            # Clean filter criteria (remove empty strings and whitespace)
            cleaned_criteria = [key.strip()
                                for key in filter_criteria if key and key.strip()]

            if not cleaned_criteria:
                warning_msg = i18n.t(
                    'components.processing.filter_data.warnings.no_valid_filter_criteria')
                self.status = warning_msg
                return Data(data={})

            # Filter the data
            filtered = {key: value for key,
                        value in data.items() if key in cleaned_criteria}

            # Check if any keys were found
            if not filtered:
                available_keys = ', '.join(data.keys()) if data else i18n.t(
                    'components.processing.filter_data.no_keys_available')
                warning_msg = i18n.t('components.processing.filter_data.warnings.no_matching_keys',
                                     criteria=', '.join(cleaned_criteria), available_keys=available_keys)
                self.status = warning_msg
                return Data(data={})

            # Create a new Data object with the filtered data
            filtered_data = Data(data=filtered)

            # Set success status
            found_keys = list(filtered.keys())
            missing_keys = [
                key for key in cleaned_criteria if key not in found_keys]

            if missing_keys:
                warning_msg = i18n.t('components.processing.filter_data.warnings.partial_match',
                                     found=len(found_keys), missing=len(missing_keys),
                                     missing_keys=', '.join(missing_keys))
                self.status = warning_msg
            else:
                success_msg = i18n.t('components.processing.filter_data.success.filtered_successfully',
                                     count=len(found_keys))
                self.status = success_msg

            return filtered_data

        except Exception as e:
            error_msg = i18n.t('components.processing.filter_data.errors.filter_failed',
                               error=str(e))
            self.status = error_msg
            return Data(data={"error": error_msg})
