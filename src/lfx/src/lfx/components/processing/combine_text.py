import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.message import Message


class CombineTextComponent(Component):
    display_name = i18n.t('components.processing.combine_text.display_name')
    description = i18n.t('components.processing.combine_text.description')
    icon = "merge"
    name = "CombineText"
    legacy: bool = True
    replacement = ["processing.DataOperations"]

    inputs = [
        MessageTextInput(
            name="text1",
            display_name=i18n.t(
                'components.processing.combine_text.text1.display_name'),
            info=i18n.t('components.processing.combine_text.text1.info'),
        ),
        MessageTextInput(
            name="text2",
            display_name=i18n.t(
                'components.processing.combine_text.text2.display_name'),
            info=i18n.t('components.processing.combine_text.text2.info'),
        ),
        MessageTextInput(
            name="delimiter",
            display_name=i18n.t(
                'components.processing.combine_text.delimiter.display_name'),
            info=i18n.t('components.processing.combine_text.delimiter.info'),
            value=" ",
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.combine_text.outputs.combined_text.display_name'),
            name="combined_text",
            method="combine_texts"
        ),
    ]

    def combine_texts(self) -> Message:
        try:
            # Handle None or empty inputs
            text1 = self.text1 or ""
            text2 = self.text2 or ""
            delimiter = self.delimiter if self.delimiter is not None else " "

            # Check if both texts are empty
            if not text1 and not text2:
                warning_message = i18n.t(
                    'components.processing.combine_text.warnings.both_texts_empty')
                self.status = warning_message
                return Message(text="")

            # Combine texts
            combined = delimiter.join(filter(None, [text1, text2]))

            success_message = i18n.t('components.processing.combine_text.success.texts_combined',
                                     length=len(combined))
            self.status = success_message

            return Message(text=combined)

        except Exception as e:
            error_message = i18n.t('components.processing.combine_text.errors.combination_failed',
                                   error=str(e))
            self.status = error_message
            return Message(text=error_message)
