import os

import i18n
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import StrInput
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class GetEnvVar(Component):
    display_name = i18n.t('components.datastax.getenvvar.display_name')
    description = i18n.t('components.datastax.getenvvar.description')
    icon = "AstraDB"

    inputs = [
        StrInput(
            name="env_var_name",
            display_name=i18n.t(
                'components.datastax.getenvvar.env_var_name.display_name'),
            info=i18n.t('components.datastax.getenvvar.env_var_name.info'),
        )
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.getenvvar.outputs.env_var_value.display_name'),
            name="env_var_value",
            method="process_inputs"
        ),
    ]

    def process_inputs(self) -> Message:
        """Get the value of an environment variable.

        Returns:
            Message: Message containing the environment variable value.

        Raises:
            ValueError: If the environment variable is not set.
        """
        try:
            logger.info(i18n.t('components.datastax.getenvvar.logs.getting_env_var',
                               var_name=self.env_var_name))
            self.status = i18n.t(
                'components.datastax.getenvvar.status.getting')

            if self.env_var_name not in os.environ:
                error_msg = i18n.t('components.datastax.getenvvar.errors.env_var_not_set',
                                   var_name=self.env_var_name)
                logger.error(error_msg)
                self.status = error_msg
                raise ValueError(error_msg)

            env_var_value = os.environ[self.env_var_name]
            success_msg = i18n.t('components.datastax.getenvvar.status.retrieved',
                                 var_name=self.env_var_name)
            self.status = success_msg
            logger.info(success_msg)

            # Don't log the actual value for security reasons
            logger.debug(i18n.t('components.datastax.getenvvar.logs.value_length',
                                length=len(env_var_value)))

            return Message(text=env_var_value)

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.datastax.getenvvar.errors.retrieval_failed',
                               var_name=self.env_var_name,
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
