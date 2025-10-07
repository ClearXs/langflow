from typing import Any, Generator
import i18n

from lfx.custom.custom_component.component import Component
from lfx.helpers.data import safe_convert
from lfx.inputs.inputs import BoolInput, DropdownInput, HandleInput, MessageTextInput, IntInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from lfx.template.field.base import Output


class TextOutputComponent(Component):
    display_name = i18n.t('components.input_output.text_output.display_name')
    description = i18n.t('components.input_output.text_output.description')
    documentation: str = "https://docs.langflow.org/components-io#text-output"
    icon = "Type"
    name = "TextOutput"

    inputs = [
        HandleInput(
            name="input_value",
            display_name=i18n.t(
                'components.input_output.text_output.input_value.display_name'),
            info=i18n.t(
                'components.input_output.text_output.input_value.info'),
            input_types=["Data", "DataFrame", "Message", "Text"],
            required=True,
        ),
        MessageTextInput(
            name="template",
            display_name=i18n.t(
                'components.input_output.text_output.template.display_name'),
            info=i18n.t('components.input_output.text_output.template.info'),
            placeholder="{text}",
            advanced=True,
        ),
        BoolInput(
            name="clean_data",
            display_name=i18n.t(
                'components.input_output.text_output.clean_data.display_name'),
            info=i18n.t('components.input_output.text_output.clean_data.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="output_format",
            display_name=i18n.t(
                'components.input_output.text_output.output_format.display_name'),
            info=i18n.t(
                'components.input_output.text_output.output_format.info'),
            options=["text", "markdown", "json", "html"],
            value="text",
            advanced=True,
        ),
        BoolInput(
            name="preserve_whitespace",
            display_name=i18n.t(
                'components.input_output.text_output.preserve_whitespace.display_name'),
            info=i18n.t(
                'components.input_output.text_output.preserve_whitespace.info'),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="max_length",
            display_name=i18n.t(
                'components.input_output.text_output.max_length.display_name'),
            info=i18n.t('components.input_output.text_output.max_length.info'),
            value=0,
            range_spec=(0, 100000),
            advanced=True,
        ),
        BoolInput(
            name="show_line_numbers",
            display_name=i18n.t(
                'components.input_output.text_output.show_line_numbers.display_name'),
            info=i18n.t(
                'components.input_output.text_output.show_line_numbers.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="prefix",
            display_name=i18n.t(
                'components.input_output.text_output.prefix.display_name'),
            info=i18n.t('components.input_output.text_output.prefix.info'),
            placeholder="Output: ",
            advanced=True,
        ),
        MessageTextInput(
            name="suffix",
            display_name=i18n.t(
                'components.input_output.text_output.suffix.display_name'),
            info=i18n.t('components.input_output.text_output.suffix.info'),
            placeholder="",
            advanced=True,
        ),
        BoolInput(
            name="enable_streaming",
            display_name=i18n.t(
                'components.input_output.text_output.enable_streaming.display_name'),
            info=i18n.t(
                'components.input_output.text_output.enable_streaming.info'),
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.input_output.text_output.outputs.text.display_name'),
            name="text",
            method="get_text_output",
        ),
        Output(
            display_name=i18n.t(
                'components.input_output.text_output.outputs.formatted_output.display_name'),
            name="formatted_output",
            method="get_formatted_output",
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "output_format":
            # Show/hide format-specific options
            if field_value == "json":
                build_config["preserve_whitespace"]["show"] = False
                build_config["show_line_numbers"]["show"] = True
            elif field_value == "markdown":
                build_config["preserve_whitespace"]["show"] = True
                build_config["show_line_numbers"]["show"] = False
            elif field_value == "html":
                build_config["preserve_whitespace"]["show"] = False
                build_config["show_line_numbers"]["show"] = False
            else:  # text
                build_config["preserve_whitespace"]["show"] = True
                build_config["show_line_numbers"]["show"] = True

        if field_name == "enable_streaming":
            # Streaming mode affects some options
            if field_value:
                build_config["max_length"]["show"] = False
            else:
                build_config["max_length"]["show"] = True

        return build_config

    def _validate_inputs(self) -> None:
        """Validate the component inputs."""
        if self.input_value is None:
            error_message = i18n.t(
                'components.input_output.text_output.errors.input_cannot_be_none')
            self.status = error_message
            raise ValueError(error_message)

        if self.max_length < 0:
            error_message = i18n.t(
                'components.input_output.text_output.errors.invalid_max_length')
            self.status = error_message
            raise ValueError(error_message)

    def _convert_input_to_string(self) -> str | Generator[Any, None, None]:
        """Convert input data to string format."""
        if isinstance(self.input_value, list):
            # Handle list of items
            clean_data: bool = getattr(self, "clean_data", False)
            return "\n".join([safe_convert(item, clean_data=clean_data) for item in self.input_value])

        if isinstance(self.input_value, Generator):
            # Handle streaming data
            if self.enable_streaming:
                return self.input_value
            else:
                # Convert generator to string
                return "".join(str(chunk) for chunk in self.input_value)

        # Handle single items
        return safe_convert(self.input_value, clean_data=self.clean_data)

    def _apply_template(self, text: str) -> str:
        """Apply template formatting to the text."""
        if not self.template or not self.template.strip():
            return text

        try:
            # Simple template substitution
            if "{text}" in self.template:
                return self.template.replace("{text}", text)
            else:
                # If no {text} placeholder, append text to template
                return f"{self.template}{text}"
        except Exception as e:
            warning_message = i18n.t(
                'components.input_output.text_output.warnings.template_error', error=str(e))
            self.status = warning_message
            return text

    def _format_output(self, text: str) -> str:
        """Format the output text based on the selected format."""
        try:
            if self.output_format == "markdown":
                # Wrap in markdown code block if not already formatted
                if not text.startswith("```"):
                    text = f"```\n{text}\n```"

            elif self.output_format == "json":
                import json
                try:
                    # Try to parse and reformat as JSON
                    if isinstance(self.input_value, (Data, dict)):
                        if hasattr(self.input_value, 'data'):
                            json_data = self.input_value.data
                        else:
                            json_data = self.input_value
                        text = json.dumps(json_data, indent=2,
                                          ensure_ascii=False)
                    else:
                        # Try to parse existing text as JSON and reformat
                        parsed = json.loads(text)
                        text = json.dumps(parsed, indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, AttributeError):
                    # If not valid JSON, wrap as JSON string
                    text = json.dumps(text, ensure_ascii=False)

            elif self.output_format == "html":
                # Basic HTML formatting
                text = text.replace('\n', '<br>\n')
                text = f"<div>{text}</div>"

            # Apply whitespace preservation
            if not self.preserve_whitespace and self.output_format != "json":
                lines = text.split('\n')
                text = '\n'.join(line.strip()
                                 for line in lines if line.strip())

            return text

        except Exception as e:
            error_message = i18n.t('components.input_output.text_output.errors.format_error',
                                   format=self.output_format, error=str(e))
            self.status = error_message
            return text

    def _apply_length_limit(self, text: str) -> str:
        """Apply maximum length limit to the text."""
        if self.max_length > 0 and len(text) > self.max_length:
            truncated_text = text[:self.max_length]
            warning_message = i18n.t('components.input_output.text_output.warnings.text_truncated',
                                     original=len(text), limit=self.max_length)
            self.status = warning_message
            return truncated_text + "..."
        return text

    def _add_line_numbers(self, text: str) -> str:
        """Add line numbers to the text."""
        if not self.show_line_numbers:
            return text

        lines = text.split('\n')
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d}: {line}")

        return '\n'.join(numbered_lines)

    def _add_prefix_suffix(self, text: str) -> str:
        """Add prefix and suffix to the text."""
        result = text

        if self.prefix and self.prefix.strip():
            result = self.prefix + result

        if self.suffix and self.suffix.strip():
            result = result + self.suffix

        return result

    def get_text_output(self) -> str | Generator[Any, None, None]:
        """Get the basic text output."""
        try:
            self._validate_inputs()

            # Convert input to string
            text = self._convert_input_to_string()

            # Handle streaming
            if isinstance(text, Generator):
                return text

            # Apply template if specified
            text = self._apply_template(text)

            # Apply length limit
            text = self._apply_length_limit(text)

            # Add prefix and suffix
            text = self._add_prefix_suffix(text)

            success_message = i18n.t('components.input_output.text_output.success.text_processed',
                                     length=len(text))
            self.status = success_message

            return text

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.text_output.errors.text_output_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_formatted_output(self) -> str:
        """Get the formatted text output."""
        try:
            self._validate_inputs()

            # Get basic text output
            text = self.get_text_output()

            # Handle streaming case
            if isinstance(text, Generator):
                text = "".join(str(chunk) for chunk in text)

            # Apply formatting
            text = self._format_output(text)

            # Add line numbers if requested
            text = self._add_line_numbers(text)

            success_message = i18n.t('components.input_output.text_output.success.formatted_output_processed',
                                     format=self.output_format, length=len(text))
            self.status = success_message

            return text

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.text_output.errors.formatted_output_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_output_info(self) -> dict[str, Any]:
        """Get information about the output processing."""
        try:
            text = self.get_text_output()
            if isinstance(text, Generator):
                text_length = 0  # Can't determine length of generator
                is_streaming = True
            else:
                text_length = len(text)
                is_streaming = False

            return {
                "text_length": text_length,
                "output_format": self.output_format,
                "is_streaming": is_streaming,
                "has_template": bool(self.template and self.template.strip()),
                "has_prefix": bool(self.prefix and self.prefix.strip()),
                "has_suffix": bool(self.suffix and self.suffix.strip()),
                "max_length_applied": self.max_length > 0,
                "line_numbers_shown": self.show_line_numbers,
                "whitespace_preserved": self.preserve_whitespace,
                "data_cleaned": self.clean_data,
            }

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.text_output.errors.output_info_error', error=str(e))
            self.status = error_message
            return {"error": str(e)}
