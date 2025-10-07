import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import StrInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.template.field.base import Output


class CreateListComponent(Component):
    display_name = i18n.t('components.helpers.create_list.display_name')
    description = i18n.t('components.helpers.create_list.description')
    icon = "list"
    name = "CreateList"
    legacy = True

    inputs = [
        StrInput(
            name="texts",
            display_name=i18n.t(
                'components.helpers.create_list.texts.display_name'),
            info=i18n.t('components.helpers.create_list.texts.info'),
            is_list=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.create_list.outputs.list.display_name'),
            name="list",
            method="create_list"
        ),
        Output(
            display_name=i18n.t(
                'components.helpers.create_list.outputs.dataframe.display_name'),
            name="dataframe",
            method="as_dataframe"
        ),
    ]

    def create_list(self) -> list[Data]:
        try:
            if not self.texts:
                warning_message = i18n.t(
                    'components.helpers.create_list.warnings.empty_texts')
                self.status = warning_message
                return [Data(data={"warning": warning_message})]

            # Filter out empty or None texts
            valid_texts = [
                text for text in self.texts if text and text.strip()]

            if not valid_texts:
                warning_message = i18n.t(
                    'components.helpers.create_list.warnings.no_valid_texts')
                self.status = warning_message
                return [Data(data={"warning": warning_message})]

            data = [Data(text=text.strip()) for text in valid_texts]

            success_message = i18n.t(
                'components.helpers.create_list.success.list_created', count=len(data))
            self.status = success_message

            return data

        except Exception as e:
            error_message = i18n.t(
                'components.helpers.create_list.errors.creation_failed', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message})]

    def as_dataframe(self) -> DataFrame:
        """Convert the list of Data objects into a DataFrame.

        Returns:
            DataFrame: A DataFrame containing the list data.
        """
        try:
            data_list = self.create_list()

            # Check if the data list contains errors or warnings
            if len(data_list) == 1 and "error" in data_list[0].data:
                error_message = i18n.t(
                    'components.helpers.create_list.errors.dataframe_creation_failed_with_error')
                self.status = error_message
                return DataFrame([Data(data={"error": error_message})])

            if len(data_list) == 1 and "warning" in data_list[0].data:
                warning_message = i18n.t(
                    'components.helpers.create_list.warnings.dataframe_creation_with_warning')
                self.status = warning_message
                return DataFrame([Data(data={"warning": warning_message})])

            dataframe = DataFrame(data_list)

            success_message = i18n.t('components.helpers.create_list.success.dataframe_created',
                                     rows=len(data_list))
            self.status = success_message

            return dataframe

        except Exception as e:
            error_message = i18n.t('components.helpers.create_list.errors.dataframe_conversion_failed',
                                   error=str(e))
            self.status = error_message
            return DataFrame([Data(data={"error": error_message})])
