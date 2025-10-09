import i18n
from typing import Any

from langchain_text_splitters import CharacterTextSplitter, TextSplitter

from lfx.base.textsplitters.model import LCTextSplitterComponent
from lfx.inputs.inputs import DataInput, IntInput, MessageTextInput
from lfx.utils.util import unescape_string


class CharacterTextSplitterComponent(LCTextSplitterComponent):
    display_name = i18n.t(
        'components.langchain_utilities.character.display_name')
    description = i18n.t(
        'components.langchain_utilities.character.description')
    documentation = "https://docs.langflow.org/components/text-splitters#charactertextsplitter"
    name = "CharacterTextSplitter"
    icon = "LangChain"

    inputs = [
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.langchain_utilities.character.chunk_size.display_name'),
            info=i18n.t(
                'components.langchain_utilities.character.chunk_size.info'),
            value=1000,
        ),
        IntInput(
            name="chunk_overlap",
            display_name=i18n.t(
                'components.langchain_utilities.character.chunk_overlap.display_name'),
            info=i18n.t(
                'components.langchain_utilities.character.chunk_overlap.info'),
            value=200,
        ),
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.langchain_utilities.character.data_input.display_name'),
            info=i18n.t(
                'components.langchain_utilities.character.data_input.info'),
            input_types=["Document", "Data"],
            required=True,
        ),
        MessageTextInput(
            name="separator",
            display_name=i18n.t(
                'components.langchain_utilities.character.separator.display_name'),
            info=i18n.t(
                'components.langchain_utilities.character.separator.info'),
        ),
    ]

    def get_data_input(self) -> Any:
        return self.data_input

    def build_text_splitter(self) -> TextSplitter:
        separator = unescape_string(
            self.separator) if self.separator else "\n\n"
        return CharacterTextSplitter(
            chunk_overlap=self.chunk_overlap,
            chunk_size=self.chunk_size,
            separator=separator,
        )
