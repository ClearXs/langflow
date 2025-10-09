import i18n
from typing import Any

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter, TextSplitter

from lfx.base.textsplitters.model import LCTextSplitterComponent
from lfx.inputs.inputs import DataInput, DropdownInput, IntInput


class LanguageRecursiveTextSplitterComponent(LCTextSplitterComponent):
    display_name: str = i18n.t(
        'components.langchain_utilities.language_recursive.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.language_recursive.description')
    documentation: str = "https://docs.langflow.org/components/text-splitters#languagerecursivetextsplitter"
    name = "LanguageRecursiveTextSplitter"
    icon = "LangChain"

    inputs = [
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.langchain_utilities.language_recursive.chunk_size.display_name'),
            info=i18n.t(
                'components.langchain_utilities.language_recursive.chunk_size.info'),
            value=1000,
        ),
        IntInput(
            name="chunk_overlap",
            display_name=i18n.t(
                'components.langchain_utilities.language_recursive.chunk_overlap.display_name'),
            info=i18n.t(
                'components.langchain_utilities.language_recursive.chunk_overlap.info'),
            value=200,
        ),
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.langchain_utilities.language_recursive.data_input.display_name'),
            info=i18n.t(
                'components.langchain_utilities.language_recursive.data_input.info'),
            input_types=["Document", "Data"],
            required=True,
        ),
        DropdownInput(
            name="code_language",
            display_name=i18n.t(
                'components.langchain_utilities.language_recursive.code_language.display_name'),
            options=[x.value for x in Language],
            value="python"
        ),
    ]

    def get_data_input(self) -> Any:
        return self.data_input

    def build_text_splitter(self) -> TextSplitter:
        return RecursiveCharacterTextSplitter.from_language(
            language=Language(self.code_language),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
