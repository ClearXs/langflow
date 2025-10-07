from typing import Any
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, MessageTextInput, Output
from lfx.schema.data import Data


class DataFilterComponent(Component):
    display_name = i18n.t(
        'components.processing.filter_data_values.display_name')
    description = i18n.t(
        'components.processing.filter_data_values.description')
    icon = "filter"
    beta = True
    name = "FilterDataValues"
    legacy = True
    replacement = ["processing.DataOperations"]

    inputs = [
        DataInput(
            name="input_data",
            display_name=i18n.t(
                'components.processing.filter_data_values.input_data.display_name'),
            info=i18n.t(
                'components.processing.filter_data_values.input_data.info'),
            is_list=True
        ),
        MessageTextInput(
            name="filter_key",
            display_name=i18n.t(
                'components.processing.filter_data_values.filter_key.display_name'),
            info=i18n.t(
                'components.processing.filter_data_values.filter_key.info'),
            value="route",
            input_types=["Data"],
        ),
        MessageTextInput(
            name="filter_value",
            display_name=i18n.t(
                'components.processing.filter_data_values.filter_value.display_name'),
            info=i18n.t(
                'components.processing.filter_data_values.filter_value.info'),
            value="CMIP",
            input_types=["Data"],
        ),
        DropdownInput(
            name="operator",
            display_name=i18n.t(
                'components.processing.filter_data_values.operator.display_name'),
            options=[
                i18n.t('components.processing.filter_data_values.operators.equals'),
                i18n.t(
                    'components.processing.filter_data_values.operators.not_equals'),
                i18n.t('components.processing.filter_data_values.operators.contains'),
                i18n.t(
                    'components.processing.filter_data_values.operators.starts_with'),
                i18n.t('components.processing.filter_data_values.operators.ends_with')
            ],
            info=i18n.t(
                'components.processing.filter_data_values.operator.info'),
            value=i18n.t(
                'components.processing.filter_data_values.operators.equals'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.filter_data_values.outputs.filtered_data.display_name'),
            name="filtered_data",
            method="filter_data"
        ),
    ]

    def compare_values(self, item_value: Any, filter_value: str, operator: str) -> bool:
        """Compare values based on the selected operator."""
        # Map localized operator names to internal logic
        operator_map = {
            i18n.t('components.processing.filter_data_values.operators.equals'): "equals",
            i18n.t('components.processing.filter_data_values.operators.not_equals'): "not_equals",
            i18n.t('components.processing.filter_data_values.operators.contains'): "contains",
            i18n.t('components.processing.filter_data_values.operators.starts_with'): "starts_with",
            i18n.t('components.processing.filter_data_values.operators.ends_with'): "ends_with",
            # Also support English for backwards compatibility
            "equals": "equals",
            "not equals": "not_equals",
            "contains": "contains",
            "starts with": "starts_with",
            "ends with": "ends_with",
        }

        internal_operator = operator_map.get(operator, "equals")

        if internal_operator == "equals":
            return str(item_value) == filter_value
        elif internal_operator == "not_equals":
            return str(item_value) != filter_value
        elif internal_operator == "contains":
            return filter_value in str(item_value)
        elif internal_operator == "starts_with":
            return str(item_value).startswith(filter_value)
        elif internal_operator == "ends_with":
            return str(item_value).endswith(filter_value)
        else:
            return False

    def filter_data(self) -> list[Data]:
        """Filter data based on the specified criteria."""
        try:
            # Extract inputs
            input_data: list[Data] = self.input_data or []
            filter_key: str = getattr(self.filter_key, 'text', self.filter_key) if hasattr(
                self.filter_key, 'text') else str(self.filter_key)
            filter_value: str = getattr(self.filter_value, 'text', self.filter_value) if hasattr(
                self.filter_value, 'text') else str(self.filter_value)
            operator: str = self.operator

            # Validate inputs
            if not input_data:
                warning_msg = i18n.t(
                    'components.processing.filter_data_values.warnings.empty_input_data')
                self.status = warning_msg
                return []

            if not filter_key or not filter_value:
                warning_msg = i18n.t(
                    'components.processing.filter_data_values.warnings.missing_filter_params')
                self.status = warning_msg
                return input_data

            # Filter the data
            filtered_data = []
            missing_key_count = 0
            invalid_item_count = 0

            for idx, item in enumerate(input_data):
                # Validate item type
                if not isinstance(item, Data):
                    invalid_item_count += 1
                    continue

                # Check if item has data and the required key
                if isinstance(item.data, dict) and filter_key in item.data:
                    if self.compare_values(item.data[filter_key], filter_value, operator):
                        filtered_data.append(item)
                else:
                    missing_key_count += 1

            # Set status based on results
            if invalid_item_count > 0:
                warning_msg = i18n.t('components.processing.filter_data_values.warnings.invalid_items',
                                     count=invalid_item_count)
                self.status = warning_msg
            elif missing_key_count > 0:
                warning_msg = i18n.t('components.processing.filter_data_values.warnings.items_missing_key',
                                     count=missing_key_count, key=filter_key)
                self.status = warning_msg
            elif len(filtered_data) == 0:
                warning_msg = i18n.t('components.processing.filter_data_values.warnings.no_matches',
                                     operator=operator, key=filter_key, value=filter_value)
                self.status = warning_msg
            else:
                success_msg = i18n.t('components.processing.filter_data_values.success.filtered_data',
                                     filtered=len(filtered_data), total=len(input_data))
                self.status = success_msg

            return filtered_data

        except Exception as e:
            error_msg = i18n.t('components.processing.filter_data_values.errors.filter_failed',
                               error=str(e))
            self.status = error_msg
            return []
