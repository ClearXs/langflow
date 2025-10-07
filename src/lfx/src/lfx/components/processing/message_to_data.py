import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class MessageToDataComponent(Component):
    display_name = i18n.t('components.processing.message_to_data.display_name')
    description = i18n.t('components.processing.message_to_data.description')
    icon = "message-square-share"
    beta = True
    name = "MessagetoData"
    legacy = True
    replacement = ["processing.TypeConverterComponent"]

    inputs = [
        MessageInput(
            name="message",
            display_name=i18n.t(
                'components.processing.message_to_data.message.display_name'),
            info=i18n.t('components.processing.message_to_data.message.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.message_to_data.outputs.data.display_name'),
            name="data",
            method="convert_message_to_data"
        ),
    ]

    def convert_message_to_data(self) -> Data:
        try:
            # Validate input
            if not self.message:
                error_msg = i18n.t(
                    'components.processing.message_to_data.errors.empty_message')
                self.status = error_msg
                logger.debug(error_msg)
                return Data(data={"error": error_msg})

            # Check for Message by checking if it has the expected attributes instead of isinstance
            if hasattr(self.message, "data") and hasattr(self.message, "text") and hasattr(self.message, "get_text"):
                # Convert Message to Data - this works for both langflow.Message and lfx.Message
                converted_data = Data(data=self.message.data)

                success_msg = i18n.t(
                    'components.processing.message_to_data.success.conversion_successful')
                self.status = success_msg
                logger.debug(success_msg)

                return converted_data
            else:
                error_msg = i18n.t(
                    'components.processing.message_to_data.errors.invalid_message_type')
                self.status = error_msg
                logger.debug(error_msg, exc_info=True)
                return Data(data={"error": error_msg})

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.message_to_data.errors.conversion_failed', error=str(e))
            self.status = error_msg
            logger.error(error_msg, exc_info=True)
            return Data(data={"error": error_msg})
