import i18n
from typing import Any

from langchain_text_splitters import NLTKTextSplitter, TextSplitter

from lfx.base.textsplitters.model import LCTextSplitterComponent
from lfx.inputs.inputs import DataInput, IntInput, MessageTextInput
from lfx.utils.util import unescape_string


class NaturalLanguageTextSplitterComponent(LCTextSplitterComponent):
    display_name = i18n.t(
        'components.langchain_utilities.natural_language.display_name')
    description = i18n.t(
        'components.langchain_utilities.natural_language.description')
    documentation = (
        "https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/split_by_token/#nltk"
    )
    name = "NaturalLanguageTextSplitter"
    icon = "LangChain"
    inputs = [
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.langchain_utilities.natural_language.chunk_size.display_name'),
            info=i18n.t(
                'components.langchain_utilities.natural_language.chunk_size.info'),
            value=1000,
        ),
        IntInput(
            name="chunk_overlap",
            display_name=i18n.t(
                'components.langchain_utilities.natural_language.chunk_overlap.display_name'),
            info=i18n.t(
                'components.langchain_utilities.natural_language.chunk_overlap.info'),
            value=200,
        ),
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.langchain_utilities.natural_language.data_input.display_name'),
            info=i18n.t(
                'components.langchain_utilities.natural_language.data_input.info'),
            input_types=["Document", "Data"],
            required=True,
        ),
        MessageTextInput(
            name="separator",
            display_name=i18n.t(
                'components.langchain_utilities.natural_language.separator.display_name'),
            info=i18n.t(
                'components.langchain_utilities.natural_language.separator.info'),
        ),
        MessageTextInput(
            name="language",
            display_name=i18n.t(
                'components.langchain_utilities.natural_language.language.display_name'),
            info=i18n.t(
                'components.langchain_utilities.natural_language.language.info'),
        ),
    ]

    def get_data_input(self) -> Any:
        return self.data_input

    def build_text_splitter(self) -> TextSplitter:
        separator = unescape_string(
            self.separator) if self.separator else "\n\n"
        return NLTKTextSplitter(
            language=self.language.lower() if self.language else "english",
            separator=separator,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
