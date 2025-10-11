import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import DropdownInput, FloatInput, IntInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.message import Message


class VectaraRagComponent(Component):
    display_name = i18n.t('components.vectorstores.vectara_rag.display_name')
    description = i18n.t('components.vectorstores.vectara_rag.description')
    documentation = "https://docs.vectara.com/docs"
    icon = "Vectara"
    name = "VectaraRAG"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    SUMMARIZER_PROMPTS = [
        "vectara-summary-ext-24-05-sml",
        "vectara-summary-ext-24-05-med-omni",
        "vectara-summary-ext-24-05-large",
        "vectara-summary-ext-24-05-med",
        "vectara-summary-ext-v1.3.0",
    ]

    RERANKER_TYPES = ["mmr", "rerank_multilingual_v1", "none"]

    RESPONSE_LANGUAGES = [
        "auto",
        "eng",
        "spa",
        "fra",
        "zho",
        "deu",
        "hin",
        "ara",
        "por",
        "ita",
        "jpn",
        "kor",
        "rus",
        "tur",
        "fas",
        "vie",
        "tha",
        "heb",
        "nld",
        "ind",
        "pol",
        "ukr",
        "ron",
        "swe",
        "ces",
        "ell",
        "ben",
        "msa",
        "urd",
    ]

    field_order = ["vectara_customer_id", "vectara_corpus_id",
                   "vectara_api_key", "search_query", "reranker"]

    inputs = [
        StrInput(
            name="vectara_customer_id",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.vectara_customer_id.display_name'),
            required=True
        ),
        StrInput(
            name="vectara_corpus_id",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.vectara_corpus_id.display_name'),
            required=True
        ),
        SecretStrInput(
            name="vectara_api_key",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.vectara_api_key.display_name'),
            required=True
        ),
        MessageTextInput(
            name="search_query",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.search_query.display_name'),
            info=i18n.t(
                'components.vectorstores.vectara_rag.search_query.info'),
            tool_mode=True,
        ),
        FloatInput(
            name="lexical_interpolation",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.lexical_interpolation.display_name'),
            range_spec=RangeSpec(min=0.005, max=0.1, step=0.005),
            value=0.005,
            advanced=True,
            info=i18n.t(
                'components.vectorstores.vectara_rag.lexical_interpolation.info'),
        ),
        MessageTextInput(
            name="filter",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.filter.display_name'),
            value="",
            advanced=True,
            info=i18n.t('components.vectorstores.vectara_rag.filter.info'),
        ),
        DropdownInput(
            name="reranker",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.reranker.display_name'),
            options=RERANKER_TYPES,
            value=RERANKER_TYPES[0],
            info=i18n.t('components.vectorstores.vectara_rag.reranker.info'),
        ),
        IntInput(
            name="reranker_k",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.reranker_k.display_name'),
            value=50,
            range_spec=RangeSpec(min=1, max=100, step=1),
            advanced=True,
        ),
        FloatInput(
            name="diversity_bias",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.diversity_bias.display_name'),
            value=0.2,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
            info=i18n.t(
                'components.vectorstores.vectara_rag.diversity_bias.info'),
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.max_results.display_name'),
            value=7,
            range_spec=RangeSpec(min=1, max=100, step=1),
            advanced=True,
            info=i18n.t(
                'components.vectorstores.vectara_rag.max_results.info'),
        ),
        DropdownInput(
            name="response_lang",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.response_lang.display_name'),
            options=RESPONSE_LANGUAGES,
            value="eng",
            advanced=True,
            info=i18n.t(
                'components.vectorstores.vectara_rag.response_lang.info'),
        ),
        DropdownInput(
            name="prompt",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.prompt.display_name'),
            options=SUMMARIZER_PROMPTS,
            value=SUMMARIZER_PROMPTS[0],
            advanced=True,
            info=i18n.t('components.vectorstores.vectara_rag.prompt.info'),
        ),
    ]

    outputs = [
        Output(
            name="answer",
            display_name=i18n.t(
                'components.vectorstores.vectara_rag.outputs.answer'),
            method="generate_response"
        ),
    ]

    def generate_response(
        self,
    ) -> Message:
        text_output = ""

        try:
            from langchain_community.vectorstores import Vectara
            from langchain_community.vectorstores.vectara import RerankConfig, SummaryConfig, VectaraQueryConfig
        except ImportError as e:
            msg = "Could not import Vectara. Please install it with `pip install langchain-community`."
            raise ImportError(msg) from e

        vectara = Vectara(self.vectara_customer_id,
                          self.vectara_corpus_id, self.vectara_api_key)
        rerank_config = RerankConfig(
            self.reranker, self.reranker_k, self.diversity_bias)
        summary_config = SummaryConfig(
            is_enabled=True, max_results=self.max_results, response_lang=self.response_lang, prompt_name=self.prompt
        )
        config = VectaraQueryConfig(
            lambda_val=self.lexical_interpolation,
            filter=self.filter,
            summary_config=summary_config,
            rerank_config=rerank_config,
        )
        rag = vectara.as_rag(config)
        response = rag.invoke(self.search_query, config={
                              "callbacks": self.get_langchain_callbacks()})

        text_output = response["answer"]

        return Message(text=text_output)
