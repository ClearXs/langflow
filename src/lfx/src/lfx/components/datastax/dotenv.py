import io

import i18n
from dotenv import load_dotenv

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MultilineSecretInput
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class Dotenv(Component):
    display_name = i18n.t('components.datastax.dotenv.display_name')
    description = i18n.t('components.datastax.dotenv.description')
    icon = "AstraDB"

    inputs = [
        MultilineSecretInput(
            name="dotenv_file_content",
            display_name=i18n.t(
                'components.datastax.dotenv.dotenv_file_content.display_name'),
            info=i18n.t('components.datastax.dotenv.dotenv_file_content.info'),
        )
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.dotenv.outputs.env_set.display_name'),
            name="env_set",
            method="process_inputs"
        ),
    ]

    def process_inputs(self) -> Message:
        """Load environment variables from .env file content.

        Returns:
            Message: Status message indicating success or failure.

        Raises:
            ValueError: If loading fails.
        """
        try:
            logger.info(
                i18n.t('components.datastax.dotenv.logs.loading_env_vars'))
            self.status = i18n.t('components.datastax.dotenv.status.loading')

            fake_file = io.StringIO(self.dotenv_file_content)
            result = load_dotenv(stream=fake_file, override=True)

            if result:
                success_msg = i18n.t(
                    'components.datastax.dotenv.status.loaded')
                logger.info(success_msg)
                self.status = success_msg
                return Message(text=success_msg)
            else:
                warning_msg = i18n.t(
                    'components.datastax.dotenv.warnings.no_variables_found')
                logger.warning(warning_msg)
                self.status = warning_msg
                return Message(text=warning_msg)

        except Exception as e:
            error_msg = i18n.t('components.datastax.dotenv.errors.load_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
