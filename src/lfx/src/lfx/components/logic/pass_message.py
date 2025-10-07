import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageInput
from lfx.schema.message import Message
from lfx.template.field.base import Output


class PassMessageComponent(Component):
    display_name = i18n.t('components.logic.pass_message.display_name')
    description = i18n.t('components.logic.pass_message.description')
    name = "Pass"
    icon = "arrow-right"
    legacy: bool = True
    replacement = ["logic.ConditionalRouter"]

    inputs = [
        MessageInput(
            name="input_message",
            display_name=i18n.t(
                'components.logic.pass_message.input_message.display_name'),
            info=i18n.t('components.logic.pass_message.input_message.info'),
            required=True,
        ),
        MessageInput(
            name="ignored_message",
            display_name=i18n.t(
                'components.logic.pass_message.ignored_message.display_name'),
            info=i18n.t('components.logic.pass_message.ignored_message.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.pass_message.outputs.output_message.display_name'),
            name="output_message",
            method="pass_message"
        ),
    ]

    def pass_message(self) -> Message:
        try:
            if not self.input_message:
                warning_message = i18n.t(
                    'components.logic.pass_message.warnings.empty_message')
                self.status = warning_message
                return Message(text="")

            # Set status to indicate successful pass-through
            success_message = i18n.t(
                'components.logic.pass_message.success.message_passed')
            self.status = success_message

            return self.input_message

        except Exception as e:
            error_message = i18n.t(
                'components.logic.pass_message.errors.pass_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
