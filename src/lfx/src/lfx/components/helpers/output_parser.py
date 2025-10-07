import i18n
from langchain_core.output_parsers import CommaSeparatedListOutputParser

from lfx.custom.custom_component.component import Component
from lfx.field_typing.constants import OutputParser
from lfx.io import DropdownInput, Output
from lfx.schema.message import Message


class OutputParserComponent(Component):
    display_name = i18n.t('components.helpers.output_parser.display_name')
    description = i18n.t('components.helpers.output_parser.description')
    icon = "type"
    name = "OutputParser"
    legacy = True
    replacement = ["processing.StructuredOutput", "processing.ParserComponent"]

    inputs = [
        DropdownInput(
            name="parser_type",
            display_name=i18n.t(
                'components.helpers.output_parser.parser_type.display_name'),
            options=["CSV"],
            value="CSV",
            info=i18n.t('components.helpers.output_parser.parser_type.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.output_parser.outputs.format_instructions.display_name'),
            name="format_instructions",
            info=i18n.t(
                'components.helpers.output_parser.outputs.format_instructions.info'),
            method="format_instructions",
        ),
        Output(
            display_name=i18n.t(
                'components.helpers.output_parser.outputs.output_parser.display_name'),
            name="output_parser",
            method="build_parser"
        ),
    ]

    def build_parser(self) -> OutputParser:
        try:
            if self.parser_type == "CSV":
                success_message = i18n.t(
                    'components.helpers.output_parser.success.csv_parser_created')
                self.status = success_message
                return CommaSeparatedListOutputParser()

            error_message = i18n.t('components.helpers.output_parser.errors.unsupported_parser',
                                   parser_type=self.parser_type)
            self.status = error_message
            raise ValueError(error_message)

        except Exception as e:
            error_message = i18n.t('components.helpers.output_parser.errors.parser_creation_failed',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def format_instructions(self) -> Message:
        try:
            if self.parser_type == "CSV":
                instructions = CommaSeparatedListOutputParser().get_format_instructions()
                success_message = i18n.t(
                    'components.helpers.output_parser.success.format_instructions_generated')
                self.status = success_message
                return Message(text=instructions)

            error_message = i18n.t('components.helpers.output_parser.errors.unsupported_parser_for_instructions',
                                   parser_type=self.parser_type)
            self.status = error_message
            raise ValueError(error_message)

        except Exception as e:
            error_message = i18n.t('components.helpers.output_parser.errors.instructions_generation_failed',
                                   error=str(e))
            self.status = error_message
            return Message(text=error_message)
