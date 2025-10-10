import os
import i18n
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, IntInput, MessageTextInput, MultilineInput
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class WikipediaComponent(Component):
    display_name = i18n.t('components.wikipedia.wikipedia.display_name')
    description = i18n.t('components.wikipedia.wikipedia.description')
    icon = "Wikipedia"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.wikipedia.wikipedia.input_value.display_name'),
            tool_mode=True,
        ),
        MessageTextInput(
            name="lang",
            display_name=i18n.t(
                'components.wikipedia.wikipedia.lang.display_name'),
            value="en"
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.wikipedia.wikipedia.k.display_name'),
            value=4,
            required=True
        ),
        BoolInput(
            name="load_all_available_meta",
            display_name=i18n.t(
                'components.wikipedia.wikipedia.load_all_available_meta.display_name'),
            value=False,
            advanced=True
        ),
        IntInput(
            name="doc_content_chars_max",
            display_name=i18n.t(
                'components.wikipedia.wikipedia.doc_content_chars_max.display_name'),
            value=4000,
            advanced=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.wikipedia.wikipedia.outputs.dataframe'),
            name="dataframe",
            method="fetch_content_dataframe"
        ),
    ]

    def run_model(self) -> DataFrame:
        return self.fetch_content_dataframe()

    def _build_wrapper(self) -> WikipediaAPIWrapper:
        return WikipediaAPIWrapper(
            top_k_results=self.k,
            lang=self.lang,
            load_all_available_meta=self.load_all_available_meta,
            doc_content_chars_max=self.doc_content_chars_max,
        )

    def fetch_content(self) -> list[Data]:
        wrapper = self._build_wrapper()
        docs = wrapper.load(self.input_value)
        data = [Data.from_document(doc) for doc in docs]
        self.status = data
        return data

    def fetch_content_dataframe(self) -> DataFrame:
        data = self.fetch_content()
        return DataFrame(data)
