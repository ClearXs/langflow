import re
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message


class RegexExtractorComponent(Component):
    display_name = i18n.t('components.processing.regex.display_name')
    description = i18n.t('components.processing.regex.description')
    documentation: str = "https://docs.langflow.org/components-processing#regex-extractor"
    icon = "regex"
    legacy = True
    replacement = ["processing.ParserComponent"]

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name=i18n.t(
                'components.processing.regex.input_text.display_name'),
            info=i18n.t('components.processing.regex.input_text.info'),
            required=True,
        ),
        MessageTextInput(
            name="pattern",
            display_name=i18n.t(
                'components.processing.regex.pattern.display_name'),
            info=i18n.t('components.processing.regex.pattern.info'),
            value="",
            required=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.regex.outputs.data.display_name'),
            name="data",
            method="extract_matches"
        ),
        Output(
            display_name=i18n.t(
                'components.processing.regex.outputs.message.display_name'),
            name="text",
            method="get_matches_text"
        ),
    ]

    def extract_matches(self) -> list[Data]:
        """Extract regex matches from input text and return as Data objects."""
        try:
            # Validate inputs
            if not self.pattern or not self.pattern.strip():
                warning_msg = i18n.t(
                    'components.processing.regex.warnings.empty_pattern')
                self.status = warning_msg
                return []

            if not self.input_text or not self.input_text.strip():
                warning_msg = i18n.t(
                    'components.processing.regex.warnings.empty_input_text')
                self.status = warning_msg
                return []

            # Compile regex pattern
            try:
                compiled_pattern = re.compile(self.pattern)
            except re.error as e:
                error_msg = i18n.t(
                    'components.processing.regex.errors.invalid_pattern', error=str(e))
                self.status = error_msg
                return [Data(data={"error": error_msg})]

            # Find all matches in the input text
            matches = compiled_pattern.findall(self.input_text)

            # Filter out empty matches
            filtered_matches = [
                match for match in matches if match and str(match).strip()]

            if not filtered_matches:
                warning_msg = i18n.t(
                    'components.processing.regex.warnings.no_matches')
                self.status = warning_msg
                return []

            # Convert matches to Data objects
            result = []
            for i, match in enumerate(filtered_matches):
                try:
                    # Handle different match types
                    if isinstance(match, tuple):
                        # Multiple capture groups
                        match_data = {f"group_{j}": group for j,
                                      group in enumerate(match)}
                        match_data["full_match"] = "".join(
                            str(g) for g in match if g)
                    else:
                        # Single match or single capture group
                        match_data = {"match": str(match)}

                    result.append(Data(data=match_data))

                except Exception as e:
                    error_msg = i18n.t('components.processing.regex.errors.match_processing_failed',
                                       index=i, error=str(e))
                    self.log(error_msg, "warning")
                    # Continue with other matches

            success_msg = i18n.t('components.processing.regex.success.matches_extracted',
                                 pattern=self.pattern, count=len(result))
            self.status = success_msg

            return result

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.regex.errors.extraction_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            return [Data(data={"error": error_msg})]

    def get_matches_text(self) -> Message:
        """Get matches as a formatted text message."""
        try:
            matches = self.extract_matches()

            if not matches:
                message_text = i18n.t(
                    'components.processing.regex.messages.no_matches_found')
                message = Message(text=message_text)
                self.status = message_text
                return message

            # Check if first match contains an error
            if matches and "error" in matches[0].data:
                error_text = matches[0].data["error"]
                message = Message(text=error_text)
                self.status = error_text
                return message

            # Format matches into text
            formatted_matches = []
            for i, match in enumerate(matches):
                try:
                    if "match" in match.data:
                        # Simple match
                        formatted_matches.append(match.data["match"])
                    elif "full_match" in match.data:
                        # Multiple capture groups
                        formatted_matches.append(match.data["full_match"])
                    else:
                        # Fallback: use first available value
                        first_value = next(iter(match.data.values()), "")
                        formatted_matches.append(str(first_value))

                except Exception as e:
                    error_msg = i18n.t('components.processing.regex.errors.match_formatting_failed',
                                       index=i, error=str(e))
                    self.log(error_msg, "warning")
                    # Continue with other matches

            if not formatted_matches:
                message_text = i18n.t(
                    'components.processing.regex.messages.no_valid_matches')
                message = Message(text=message_text)
                self.status = message_text
                return message

            result_text = "\n".join(formatted_matches)

            success_msg = i18n.t('components.processing.regex.success.text_formatted',
                                 count=len(formatted_matches), length=len(result_text))
            self.status = success_msg

            message = Message(text=result_text)
            return message

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.regex.errors.text_formatting_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            return Message(text=error_msg)
