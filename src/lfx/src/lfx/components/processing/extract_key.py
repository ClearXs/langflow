import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output, StrInput
from lfx.schema.data import Data


class ExtractDataKeyComponent(Component):
    display_name = i18n.t('components.processing.extract_key.display_name')
    description = i18n.t('components.processing.extract_key.description')
    icon = "key"
    name = "ExtractaKey"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.processing.extract_key.data_input.display_name'),
            info=i18n.t('components.processing.extract_key.data_input.info'),
        ),
        StrInput(
            name="key",
            display_name=i18n.t(
                'components.processing.extract_key.key.display_name'),
            info=i18n.t('components.processing.extract_key.key.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.extract_key.outputs.extracted_data.display_name'),
            name="extracted_data",
            method="extract_key"
        ),
    ]

    def extract_key(self) -> Data | list[Data]:
        try:
            key = self.key

            # Validate key input
            if not key or not key.strip():
                error_msg = i18n.t(
                    'components.processing.extract_key.errors.empty_key')
                self.status = error_msg
                return Data(data={"error": error_msg})

            key = key.strip()

            # Handle list of Data objects
            if isinstance(self.data_input, list):
                if not self.data_input:
                    warning_msg = i18n.t(
                        'components.processing.extract_key.warnings.empty_data_list')
                    self.status = warning_msg
                    return []

                result = []
                found_count = 0
                missing_count = 0

                for idx, item in enumerate(self.data_input):
                    if not isinstance(item, Data):
                        error_msg = i18n.t('components.processing.extract_key.errors.invalid_data_type_in_list',
                                           index=idx, actual_type=type(item).__name__)
                        self.status = error_msg
                        return Data(data={"error": error_msg})

                    if key in item.data:
                        extracted_value = item.data[key]
                        result.append(Data(data={key: extracted_value}))
                        found_count += 1
                    else:
                        missing_count += 1

                if found_count == 0:
                    error_msg = i18n.t('components.processing.extract_key.errors.key_not_found_in_any',
                                       key=key, total=len(self.data_input))
                    self.status = error_msg
                    return Data(data={"error": error_msg})

                if missing_count > 0:
                    warning_msg = i18n.t('components.processing.extract_key.warnings.key_missing_in_some',
                                         key=key, missing=missing_count, found=found_count)
                    self.status = warning_msg
                else:
                    success_msg = i18n.t('components.processing.extract_key.success.extracted_from_list',
                                         key=key, count=found_count)
                    self.status = success_msg

                return result

            # Handle single Data object
            elif isinstance(self.data_input, Data):
                if key in self.data_input.data:
                    extracted_value = self.data_input.data[key]
                    result = Data(data={key: extracted_value})

                    success_msg = i18n.t('components.processing.extract_key.success.extracted_from_single',
                                         key=key)
                    self.status = success_msg
                    return result
                else:
                    available_keys = ', '.join(self.data_input.data.keys()) if self.data_input.data else i18n.t(
                        'components.processing.extract_key.no_keys_available')
                    error_msg = i18n.t('components.processing.extract_key.errors.key_not_found_in_data',
                                       key=key, available_keys=available_keys)
                    self.status = error_msg
                    return Data(data={"error": error_msg})

            # Handle invalid input type
            else:
                error_msg = i18n.t('components.processing.extract_key.errors.invalid_input_type',
                                   actual_type=type(self.data_input).__name__)
                self.status = error_msg
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t('components.processing.extract_key.errors.extraction_failed',
                               error=str(e))
            self.status = error_msg
            return Data(data={"error": error_msg})
