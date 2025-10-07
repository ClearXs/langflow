import json
import unicodedata
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, MessageTextInput
from lfx.schema.message import Message
from lfx.template.field.base import Output


class JSONCleaner(Component):
    icon = "braces"
    display_name = i18n.t('components.processing.json_cleaner.display_name')
    description = i18n.t('components.processing.json_cleaner.description')
    legacy = True
    replacement = ["processing.ParserComponent"]

    inputs = [
        MessageTextInput(
            name="json_str",
            display_name=i18n.t(
                'components.processing.json_cleaner.json_str.display_name'),
            info=i18n.t('components.processing.json_cleaner.json_str.info'),
            required=True
        ),
        BoolInput(
            name="remove_control_chars",
            display_name=i18n.t(
                'components.processing.json_cleaner.remove_control_chars.display_name'),
            info=i18n.t(
                'components.processing.json_cleaner.remove_control_chars.info'),
            required=False,
            value=False,
        ),
        BoolInput(
            name="normalize_unicode",
            display_name=i18n.t(
                'components.processing.json_cleaner.normalize_unicode.display_name'),
            info=i18n.t(
                'components.processing.json_cleaner.normalize_unicode.info'),
            required=False,
            value=False,
        ),
        BoolInput(
            name="validate_json",
            display_name=i18n.t(
                'components.processing.json_cleaner.validate_json.display_name'),
            info=i18n.t(
                'components.processing.json_cleaner.validate_json.info'),
            required=False,
            value=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.json_cleaner.outputs.cleaned_json.display_name'),
            name="output",
            method="clean_json"
        ),
    ]

    def clean_json(self) -> Message:
        """Clean the input JSON string based on provided options and return the cleaned JSON string."""
        try:
            from json_repair import repair_json
        except ImportError as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.import_error')
            self.status = error_msg
            raise ImportError(error_msg) from e

        try:
            json_str = self.json_str
            remove_control_chars = self.remove_control_chars
            normalize_unicode = self.normalize_unicode
            validate_json = self.validate_json

            # Validate input
            if not json_str or not json_str.strip():
                error_msg = i18n.t(
                    'components.processing.json_cleaner.errors.empty_input')
                self.status = error_msg
                raise ValueError(error_msg)

            # Extract JSON from the string
            start = json_str.find("{")
            end = json_str.rfind("}")

            if start == -1 or end == -1:
                error_msg = i18n.t(
                    'components.processing.json_cleaner.errors.invalid_json_format')
                self.status = error_msg
                raise ValueError(error_msg)

            json_str = json_str[start: end + 1]

            # Apply cleaning options
            operations_applied = []

            if remove_control_chars:
                json_str = self._remove_control_characters(json_str)
                operations_applied.append(
                    i18n.t('components.processing.json_cleaner.operations.control_chars_removed'))

            if normalize_unicode:
                json_str = self._normalize_unicode(json_str)
                operations_applied.append(
                    i18n.t('components.processing.json_cleaner.operations.unicode_normalized'))

            if validate_json:
                json_str = self._validate_json(json_str)
                operations_applied.append(
                    i18n.t('components.processing.json_cleaner.operations.json_validated'))

            # Repair JSON using json_repair
            cleaned_json_str = repair_json(json_str)
            result = str(cleaned_json_str)

            # Set success status
            if operations_applied:
                success_msg = i18n.t('components.processing.json_cleaner.success.json_cleaned_with_operations',
                                     operations=', '.join(operations_applied))
            else:
                success_msg = i18n.t(
                    'components.processing.json_cleaner.success.json_cleaned')

            self.status = success_msg
            return Message(text=result)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.cleaning_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _remove_control_characters(self, s: str) -> str:
        """Remove control characters from the string."""
        try:
            return s.translate(self.translation_table)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.control_char_removal_failed', error=str(e))
            raise ValueError(error_msg) from e

    def _normalize_unicode(self, s: str) -> str:
        """Normalize Unicode characters in the string."""
        try:
            return unicodedata.normalize("NFC", s)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.unicode_normalization_failed', error=str(e))
            raise ValueError(error_msg) from e

    def _validate_json(self, s: str) -> str:
        """Validate the JSON string."""
        try:
            json.loads(s)
            return s
        except json.JSONDecodeError as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.json_validation_failed', error=str(e))
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.json_cleaner.errors.json_validation_error', error=str(e))
            raise ValueError(error_msg) from e

    def __init__(self, *args, **kwargs):
        # Create a translation table that maps control characters to None
        super().__init__(*args, **kwargs)
        self.translation_table = str.maketrans(
            "", "", "".join(chr(i) for i in range(32)) + chr(127))
