import i18n
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter

from lfx.base.textsplitters.model import LCTextSplitterComponent
from lfx.inputs.inputs import DataInput, IntInput, MessageTextInput
from lfx.utils.util import unescape_string


class RecursiveCharacterTextSplitterComponent(LCTextSplitterComponent):
    display_name: str = i18n.t(
        'components.langchain_utilities.recursive_character.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.recursive_character.description')
    documentation: str = "https://docs.langflow.org/components-processing"
    name = "RecursiveCharacterTextSplitter"
    icon = "LangChain"

    inputs = [
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.langchain_utilities.recursive_character.chunk_size.display_name'),
            info=i18n.t(
                'components.langchain_utilities.recursive_character.chunk_size.info'),
            value=1000,
        ),
        IntInput(
            name="chunk_overlap",
            display_name=i18n.t(
                'components.langchain_utilities.recursive_character.chunk_overlap.display_name'),
            info=i18n.t(
                'components.langchain_utilities.recursive_character.chunk_overlap.info'),
            value=200,
        ),
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.langchain_utilities.recursive_character.data_input.display_name'),
            info=i18n.t(
                'components.langchain_utilities.recursive_character.data_input.info'),
            input_types=["Document", "Data"],
            required=True,
        ),
        MessageTextInput(
            name="separators",
            display_name=i18n.t(
                'components.langchain_utilities.recursive_character.separators.display_name'),
            info=i18n.t(
                'components.langchain_utilities.recursive_character.separators.info'),
            is_list=True,
        ),
    ]

    def get_data_input(self) -> Any:
        return self.data_input

    def build_text_splitter(self) -> TextSplitter:
        if not self.separators:
            separators: list[str] | None = None
        else:
            # check if the separators list has escaped characters
            # if there are escaped characters, unescape them
            separators = [unescape_string(x) for x in self.separators]

        return RecursiveCharacterTextSplitter(
            separators=separators,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
