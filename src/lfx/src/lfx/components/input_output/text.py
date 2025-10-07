from typing import Any, Union
import re
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, DropdownInput, MessageTextInput, MultilineInput, IntInput
from lfx.schema.data import Data
from lfx.template.field.base import Output


class TextComponent(Component):
    display_name = i18n.t('components.input_output.text.display_name')
    description = i18n.t('components.input_output.text.description')
    documentation: str = "https://docs.langflow.org/components-io#text-input"
    icon = "Type"
    name = "Text"

    inputs = [
        MultilineInput(
            name="text",
            display_name=i18n.t(
                'components.input_output.text.text.display_name'),
            info=i18n.t('components.input_output.text.text.info'),
            value="",
            required=True,
            tool_mode=True,
        ),
        DropdownInput(
            name="text_type",
            display_name=i18n.t(
                'components.input_output.text.text_type.display_name'),
            info=i18n.t('components.input_output.text.text_type.info'),
            options=["plain", "template", "markdown", "html", "json"],
            value="plain",
            advanced=True,
        ),
        BoolInput(
            name="strip_whitespace",
            display_name=i18n.t(
                'components.input_output.text.strip_whitespace.display_name'),
            info=i18n.t('components.input_output.text.strip_whitespace.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="validate_format",
            display_name=i18n.t(
                'components.input_output.text.validate_format.display_name'),
            info=i18n.t('components.input_output.text.validate_format.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="template_variables",
            display_name=i18n.t(
                'components.input_output.text.template_variables.display_name'),
            info=i18n.t(
                'components.input_output.text.template_variables.info'),
            placeholder='{"name": "value", "key": "replacement"}',
            advanced=True,
        ),
        IntInput(
            name="max_length",
            display_name=i18n.t(
                'components.input_output.text.max_length.display_name'),
            info=i18n.t('components.input_output.text.max_length.info'),
            value=0,
            range_spec=(0, 1000000),
            advanced=True,
        ),
        IntInput(
            name="min_length",
            display_name=i18n.t(
                'components.input_output.text.min_length.display_name'),
            info=i18n.t('components.input_output.text.min_length.info'),
            value=0,
            range_spec=(0, 1000000),
            advanced=True,
        ),
        MessageTextInput(
            name="regex_pattern",
            display_name=i18n.t(
                'components.input_output.text.regex_pattern.display_name'),
            info=i18n.t('components.input_output.text.regex_pattern.info'),
            placeholder=r"\d+",
            advanced=True,
        ),
        BoolInput(
            name="case_sensitive",
            display_name=i18n.t(
                'components.input_output.text.case_sensitive.display_name'),
            info=i18n.t('components.input_output.text.case_sensitive.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="encoding",
            display_name=i18n.t(
                'components.input_output.text.encoding.display_name'),
            info=i18n.t('components.input_output.text.encoding.info'),
            options=["utf-8", "ascii", "latin-1", "utf-16", "utf-32"],
            value="utf-8",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.input_output.text.outputs.text.display_name'),
            name="text",
            method="get_text",
        ),
        Output(
            display_name=i18n.t(
                'components.input_output.text.outputs.data.display_name'),
            name="data",
            method="get_data",
        ),
        Output(
            display_name=i18n.t(
                'components.input_output.text.outputs.processed_text.display_name'),
            name="processed_text",
            method="get_processed_text",
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "text_type":
            # Show/hide relevant options based on text type
            if field_value == "template":
                build_config["template_variables"]["show"] = True
            else:
                build_config["template_variables"]["show"] = False

            if field_value in ["json", "html", "markdown"]:
                build_config["validate_format"]["show"] = True
            else:
                build_config["validate_format"]["show"] = False

        if field_name == "validate_format":
            # Show validation options when format validation is enabled
            if field_value:
                build_config["regex_pattern"]["show"] = True
                build_config["case_sensitive"]["show"] = True
            else:
                build_config["regex_pattern"]["show"] = False
                build_config["case_sensitive"]["show"] = False

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        # Check length constraints
        if self.min_length > 0 and len(self.text) < self.min_length:
            error_message = i18n.t('components.input_output.text.errors.text_too_short',
                                   length=len(self.text), min_length=self.min_length)
            self.status = error_message
            raise ValueError(error_message)

        if self.max_length > 0 and len(self.text) > self.max_length:
            error_message = i18n.t('components.input_output.text.errors.text_too_long',
                                   length=len(self.text), max_length=self.max_length)
            self.status = error_message
            raise ValueError(error_message)

        # Validate regex pattern if provided
        if self.validate_format and self.regex_pattern:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                if not re.search(self.regex_pattern, self.text, flags):
                    error_message = i18n.t('components.input_output.text.errors.regex_validation_failed',
                                           pattern=self.regex_pattern)
                    self.status = error_message
                    raise ValueError(error_message)
            except re.error as e:
                error_message = i18n.t('components.input_output.text.errors.invalid_regex_pattern',
                                       pattern=self.regex_pattern, error=str(e))
                self.status = error_message
                raise ValueError(error_message)

    def _validate_format(self, text: str) -> bool:
        """Validate text format based on text_type."""
        if not self.validate_format:
            return True

        try:
            if self.text_type == "json":
                import json
                json.loads(text)
            elif self.text_type == "html":
                # Basic HTML validation
                if not re.search(r'<[^>]+>', text):
                    return False
            elif self.text_type == "markdown":
                # Basic markdown validation - check for common markdown syntax
                markdown_patterns = [r'#', r'\*', r'_',
                                     r'`', r'\[.*\]\(.*\)', r'!\[.*\]\(.*\)']
                if not any(re.search(pattern, text) for pattern in markdown_patterns):
                    return False
            return True
        except Exception:
            return False

    def _process_template(self, text: str) -> str:
        """Process template variables in the text."""
        if self.text_type != "template" or not self.template_variables:
            return text

        try:
            import json
            variables = json.loads(self.template_variables)

            # Simple template variable replacement
            processed_text = text
            for key, value in variables.items():
                # Support both {key} and {{key}} formats
                processed_text = processed_text.replace(
                    f"{{{key}}}", str(value))
                processed_text = processed_text.replace(
                    f"{{{{{key}}}}}", str(value))

            return processed_text

        except json.JSONDecodeError as e:
            warning_message = i18n.t('components.input_output.text.warnings.invalid_template_variables',
                                     error=str(e))
            self.status = warning_message
            return text
        except Exception as e:
            warning_message = i18n.t('components.input_output.text.warnings.template_processing_error',
                                     error=str(e))
            self.status = warning_message
            return text

    def _clean_text(self, text: str) -> str:
        """Clean and process text based on settings."""
        processed_text = text

        # Strip whitespace if requested
        if self.strip_whitespace:
            processed_text = processed_text.strip()

        # Process encoding
        try:
            processed_text = processed_text.encode(
                self.encoding).decode(self.encoding)
        except UnicodeError as e:
            warning_message = i18n.t('components.input_output.text.warnings.encoding_error',
                                     encoding=self.encoding, error=str(e))
            self.status = warning_message

        return processed_text

    def get_text(self) -> str:
        """Get the basic text output."""
        try:
            self._validate_inputs()

            # Get base text
            text = self.text

            # Clean text
            text = self._clean_text(text)

            # Validate format if required
            if self.validate_format and not self._validate_format(text):
                error_message = i18n.t('components.input_output.text.errors.format_validation_failed',
                                       format=self.text_type)
                self.status = error_message
                raise ValueError(error_message)

            success_message = i18n.t('components.input_output.text.success.text_processed',
                                     length=len(text))
            self.status = success_message
            return text

        except Exception as e:
            error_message = i18n.t('components.input_output.text.errors.text_processing_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_data(self) -> Data:
        """Get text as Data object."""
        try:
            text = self.get_text()

            data_dict = {
                "text": text,
                "text_type": self.text_type,
                "length": len(text),
                "encoding": self.encoding,
            }

            # Add metadata
            if self.text_type == "template" and self.template_variables:
                try:
                    import json
                    data_dict["template_variables"] = json.loads(
                        self.template_variables)
                except json.JSONDecodeError:
                    pass

            return Data(data=data_dict, text_key="text")

        except Exception as e:
            error_message = i18n.t('components.input_output.text.errors.data_creation_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_processed_text(self) -> str:
        """Get fully processed text with template variables replaced."""
        try:
            self._validate_inputs()

            # Get base text
            text = self.text

            # Clean text
            text = self._clean_text(text)

            # Process template variables
            text = self._process_template(text)

            # Validate format if required
            if self.validate_format and not self._validate_format(text):
                error_message = i18n.t('components.input_output.text.errors.format_validation_failed',
                                       format=self.text_type)
                self.status = error_message
                raise ValueError(error_message)

            success_message = i18n.t('components.input_output.text.success.processed_text_created',
                                     length=len(text))
            self.status = success_message
            return text

        except Exception as e:
            error_message = i18n.t('components.input_output.text.errors.processed_text_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_text_info(self) -> dict[str, Any]:
        """Get information about the text."""
        try:
            text = self.get_text()
            processed_text = self.get_processed_text()

            return {
                "original_length": len(self.text),
                "processed_length": len(processed_text),
                "text_type": self.text_type,
                "encoding": self.encoding,
                "has_templates": self.text_type == "template" and bool(self.template_variables),
                "is_valid_format": self._validate_format(text),
                "whitespace_stripped": self.strip_whitespace,
                "validation_enabled": self.validate_format,
                "regex_pattern": self.regex_pattern if self.validate_format else None,
                "min_length": self.min_length,
                "max_length": self.max_length,
            }

        except Exception as e:
            error_message = i18n.t('components.input_output.text.errors.text_info_error',
                                   error=str(e))
            return {"error": str(e)}
