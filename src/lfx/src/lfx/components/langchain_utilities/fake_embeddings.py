import i18n
from langchain_community.embeddings import FakeEmbeddings

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.field_typing import Embeddings
from lfx.io import IntInput


class FakeEmbeddingsComponent(LCEmbeddingsModel):
    display_name = i18n.t(
        'components.langchain_utilities.fake_embeddings.display_name')
    description = i18n.t(
        'components.langchain_utilities.fake_embeddings.description')
    icon = "LangChain"
    name = "LangChainFakeEmbeddings"

    inputs = [
        IntInput(
            name="dimensions",
            display_name=i18n.t(
                'components.langchain_utilities.fake_embeddings.dimensions.display_name'),
            info=i18n.t(
                'components.langchain_utilities.fake_embeddings.dimensions.info'),
            value=5,
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        return FakeEmbeddings(
            size=self.dimensions or 5,
        )
