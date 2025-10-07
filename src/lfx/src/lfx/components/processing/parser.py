import i18n

from lfx.custom.custom_component.component import Component
from lfx.helpers.data import safe_convert
from lfx.inputs.inputs import BoolInput, HandleInput, MessageTextInput, MultilineInput, TabInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from lfx.template.field.base import Output


class ParserComponent(Component):
    display_name = i18n.t('components.processing.parser.display_name')
    description = i18n.t('components.processing.parser.description')
    documentation: str = "https://docs.langflow.org/components-processing#parser"
    icon = "braces"

    inputs = [
        HandleInput(
            name="input_data",
            display_name=i18n.t(
                'components.processing.parser.input_data.display_name'),
            input_types=["DataFrame", "Data"],
            info=i18n.t('components.processing.parser.input_data.info'),
            required=True,
        ),
        TabInput(
            name="mode",
            display_name=i18n.t(
                'components.processing.parser.mode.display_name'),
            options=[
                i18n.t('components.processing.parser.mode.parser'),
                i18n.t('components.processing.parser.mode.stringify')
            ],
            value=i18n.t('components.processing.parser.mode.parser'),
            info=i18n.t('components.processing.parser.mode.info'),
            real_time_refresh=True,
        ),
        MultilineInput(
            name="pattern",
            display_name=i18n.t(
                'components.processing.parser.pattern.display_name'),
            info=i18n.t('components.processing.parser.pattern.info'),
            value=i18n.t('components.processing.parser.pattern.default_value'),
            dynamic=True,
            show=True,
            required=True,
        ),
        MessageTextInput(
            name="sep",
            display_name=i18n.t(
                'components.processing.parser.sep.display_name'),
            advanced=True,
            value="\n",
            info=i18n.t('components.processing.parser.sep.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.parser.outputs.parsed_text.display_name'),
            name="parsed_text",
            info=i18n.t(
                'components.processing.parser.outputs.parsed_text.info'),
            method="parse_combined_text",
        ),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        """Dynamically hide/show `template` and enforce requirement based on `mode`."""
        if field_name == "mode":
            # Map localized mode values to internal values
            mode_map = {
                i18n.t('components.processing.parser.mode.parser'): "Parser",
                i18n.t('components.processing.parser.mode.stringify'): "Stringify",
                # Also support English for backwards compatibility
                "Parser": "Parser",
                "Stringify": "Stringify",
            }

            internal_mode = mode_map.get(field_value, "Parser")

            build_config["pattern"]["show"] = internal_mode == "Parser"
            build_config["pattern"]["required"] = internal_mode == "Parser"

            if internal_mode == "Stringify":
                clean_data = BoolInput(
                    name="clean_data",
                    display_name=i18n.t(
                        'components.processing.parser.clean_data.display_name'),
                    info=i18n.t(
                        'components.processing.parser.clean_data.info'),
                    value=True,
                    advanced=True,
                    required=False,
                )
                build_config["clean_data"] = clean_data.to_dict()
            else:
                build_config.pop("clean_data", None)

        return build_config

    def _clean_args(self):
        """Prepare arguments based on input type."""
        try:
            input_data = self.input_data

            match input_data:
                case list() if all(isinstance(item, Data) for item in input_data):
                    error_msg = i18n.t(
                        'components.processing.parser.errors.data_list_not_supported')
                    raise ValueError(error_msg)
                case DataFrame():
                    return input_data, None
                case Data():
                    return None, input_data
                case dict() if "data" in input_data:
                    try:
                        if "columns" in input_data:  # Likely a DataFrame
                            return DataFrame.from_dict(input_data), None
                        # Likely a Data object
                        return None, Data(**input_data)
                    except (TypeError, ValueError, KeyError) as e:
                        error_msg = i18n.t(
                            'components.processing.parser.errors.invalid_structured_input', error=str(e))
                        raise ValueError(error_msg) from e
                case _:
                    error_msg = i18n.t('components.processing.parser.errors.unsupported_input_type',
                                       actual_type=type(input_data).__name__)
                    raise ValueError(error_msg)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parser.errors.argument_preparation_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def parse_combined_text(self) -> Message:
        """Parse all rows/items into a single text or convert input to string if `stringify` is enabled."""
        try:
            # Map localized mode values to internal values
            mode_map = {
                i18n.t('components.processing.parser.mode.parser'): "Parser",
                i18n.t('components.processing.parser.mode.stringify'): "Stringify",
                # Also support English for backwards compatibility
                "Parser": "Parser",
                "Stringify": "Stringify",
            }

            internal_mode = mode_map.get(self.mode, "Parser")

            # Early return for stringify option
            if internal_mode == "Stringify":
                return self.convert_to_string()

            df, data = self._clean_args()

            if not df and not data:
                warning_msg = i18n.t(
                    'components.processing.parser.warnings.no_data_to_parse')
                self.status = warning_msg
                return Message(text="")

            lines = []

            if df is not None:
                if df.empty:
                    warning_msg = i18n.t(
                        'components.processing.parser.warnings.empty_dataframe')
                    self.status = warning_msg
                    return Message(text="")

                for row_index, row in df.iterrows():
                    try:
                        formatted_text = self.pattern.format(**row.to_dict())
                        lines.append(formatted_text)
                    except KeyError as e:
                        error_msg = i18n.t('components.processing.parser.errors.template_key_missing',
                                           row=row_index, key=str(e).strip("'\""))
                        self.log(error_msg, "warning")
                        # Continue with other rows
                    except Exception as e:
                        error_msg = i18n.t('components.processing.parser.errors.row_formatting_failed',
                                           row=row_index, error=str(e))
                        self.log(error_msg, "warning")
                        # Continue with other rows

            elif data is not None:
                if not data.data:
                    warning_msg = i18n.t(
                        'components.processing.parser.warnings.empty_data')
                    self.status = warning_msg
                    return Message(text="")

                try:
                    formatted_text = self.pattern.format(**data.data)
                    lines.append(formatted_text)
                except KeyError as e:
                    error_msg = i18n.t('components.processing.parser.errors.data_key_missing',
                                       key=str(e).strip("'\""), available_keys=', '.join(data.data.keys()))
                    self.status = error_msg
                    raise ValueError(error_msg)
                except Exception as e:
                    error_msg = i18n.t(
                        'components.processing.parser.errors.data_formatting_failed', error=str(e))
                    self.status = error_msg
                    raise ValueError(error_msg) from e

            if not lines:
                warning_msg = i18n.t(
                    'components.processing.parser.warnings.no_lines_generated')
                self.status = warning_msg
                return Message(text="")

            combined_text = self.sep.join(lines)

            success_msg = i18n.t('components.processing.parser.success.text_parsed',
                                 lines=len(lines), length=len(combined_text))
            self.status = success_msg

            return Message(text=combined_text)

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parser.errors.parsing_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def convert_to_string(self) -> Message:
        """Convert input data to string with proper error handling."""
        try:
            result = ""

            if isinstance(self.input_data, list):
                if not self.input_data:
                    warning_msg = i18n.t(
                        'components.processing.parser.warnings.empty_input_list')
                    self.status = warning_msg
                    return Message(text="")

                clean_data = getattr(self, 'clean_data', False)
                converted_items = []

                for i, item in enumerate(self.input_data):
                    try:
                        converted = safe_convert(item, clean_data=clean_data)
                        converted_items.append(converted)
                    except Exception as e:
                        error_msg = i18n.t('components.processing.parser.errors.list_item_conversion_failed',
                                           index=i, error=str(e))
                        self.log(error_msg, "warning")
                        # Continue with other items

                result = "\n".join(converted_items)
            else:
                if not self.input_data:
                    warning_msg = i18n.t(
                        'components.processing.parser.warnings.empty_input_data')
                    self.status = warning_msg
                    return Message(text="")

                clean_data = getattr(self, 'clean_data', False)
                result = safe_convert(self.input_data, clean_data=clean_data)

            log_msg = i18n.t(
                'components.processing.parser.logs.string_conversion_completed', length=len(result))
            self.log(log_msg)

            success_msg = i18n.t(
                'components.processing.parser.success.string_converted', length=len(result))
            self.status = success_msg

            message = Message(text=result)
            return message

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.parser.errors.string_conversion_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e
