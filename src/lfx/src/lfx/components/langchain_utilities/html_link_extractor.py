import i18n
from typing import Any

from langchain_community.graph_vectorstores.extractors import HtmlLinkExtractor, LinkExtractorTransformer
from langchain_core.documents import BaseDocumentTransformer

from lfx.base.document_transformers.model import LCDocumentTransformerComponent
from lfx.inputs.inputs import BoolInput, DataInput, StrInput


class HtmlLinkExtractorComponent(LCDocumentTransformerComponent):
    display_name = i18n.t(
        'components.langchain_utilities.html_link_extractor.display_name')
    description = i18n.t(
        'components.langchain_utilities.html_link_extractor.description')
    documentation = "https://python.langchain.org/v0.2/api_reference/community/graph_vectorstores/langchain_community.graph_vectorstores.extractors.html_link_extractor.HtmlLinkExtractor.html"
    name = "HtmlLinkExtractor"
    icon = "LangChain"

    inputs = [
        StrInput(
            name="kind",
            display_name=i18n.t(
                'components.langchain_utilities.html_link_extractor.kind.display_name'),
            info=i18n.t(
                'components.langchain_utilities.html_link_extractor.kind.info'),
            value="hyperlink",
            required=False
        ),
        BoolInput(
            name="drop_fragments",
            display_name=i18n.t(
                'components.langchain_utilities.html_link_extractor.drop_fragments.display_name'),
            info=i18n.t(
                'components.langchain_utilities.html_link_extractor.drop_fragments.info'),
            value=True,
            required=False
        ),
        DataInput(
            name="data_input",
            display_name=i18n.t(
                'components.langchain_utilities.html_link_extractor.data_input.display_name'),
            info=i18n.t(
                'components.langchain_utilities.html_link_extractor.data_input.info'),
            input_types=["Document", "Data"],
            required=True,
        ),
    ]

    def get_data_input(self) -> Any:
        return self.data_input

    def build_document_transformer(self) -> BaseDocumentTransformer:
        return LinkExtractorTransformer(
            [HtmlLinkExtractor(
                kind=self.kind, drop_fragments=self.drop_fragments).as_document_extractor()]
        )
