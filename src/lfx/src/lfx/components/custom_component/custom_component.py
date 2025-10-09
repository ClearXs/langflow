import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class CustomComponent(Component):
    display_name = i18n.t(
        'components.custom_component.custom_component.display_name')
    description = i18n.t(
        'components.custom_component.custom_component.description')
    documentation: str = "https://docs.langflow.org/components-custom-components"
    icon = "code"
    name = "CustomComponent"

    inputs = [
        MessageTextInput(
            name="input_value",
            display_name=i18n.t(
                'components.custom_component.custom_component.input_value.display_name'),
            info=i18n.t(
                'components.custom_component.custom_component.input_value.info'),
            value="Hello, World!",
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.custom_component.custom_component.outputs.output.display_name'),
            name="output",
            method="build_output"
        ),
    ]

    def build_output(self) -> Data:
        """Build output data from input value.

        Returns:
            Data: Data object containing the input value.

        Raises:
            ValueError: If data creation fails.
        """
        try:
            logger.info(
                i18n.t('components.custom_component.custom_component.logs.building_output'))
            self.status = i18n.t(
                'components.custom_component.custom_component.status.building')

            logger.debug(i18n.t('components.custom_component.custom_component.logs.creating_data',
                                value_length=len(str(self.input_value))))

            data = Data(value=self.input_value)

            success_msg = i18n.t(
                'components.custom_component.custom_component.status.output_created')
            self.status = data
            logger.info(success_msg)

            return data

        except Exception as e:
            error_msg = i18n.t('components.custom_component.custom_component.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
