import i18n
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.message import Message


class SelfQueryRetrieverComponent(Component):
    display_name = i18n.t(
        'components.langchain_utilities.self_query.display_name')
    description = i18n.t(
        'components.langchain_utilities.self_query.description')
    name = "SelfQueryRetriever"
    icon = "LangChain"
    legacy: bool = True

    inputs = [
        HandleInput(
            name="query",
            display_name=i18n.t(
                'components.langchain_utilities.self_query.query.display_name'),
            info=i18n.t(
                'components.langchain_utilities.self_query.query.info'),
            input_types=["Message"],
        ),
        HandleInput(
            name="vectorstore",
            display_name=i18n.t(
                'components.langchain_utilities.self_query.vectorstore.display_name'),
            info=i18n.t(
                'components.langchain_utilities.self_query.vectorstore.info'),
            input_types=["VectorStore"],
        ),
        HandleInput(
            name="attribute_infos",
            display_name=i18n.t(
                'components.langchain_utilities.self_query.attribute_infos.display_name'),
            info=i18n.t(
                'components.langchain_utilities.self_query.attribute_infos.info'),
            input_types=["Data"],
            is_list=True,
        ),
        MessageTextInput(
            name="document_content_description",
            display_name=i18n.t(
                'components.langchain_utilities.self_query.document_content_description.display_name'),
            info=i18n.t(
                'components.langchain_utilities.self_query.document_content_description.info'),
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.self_query.llm.display_name'),
            info=i18n.t('components.langchain_utilities.self_query.llm.info'),
            input_types=["LanguageModel"],
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.self_query.outputs.documents.display_name'),
            name="documents",
            method="retrieve_documents",
        ),
    ]

    def retrieve_documents(self) -> list[Data]:
        metadata_field_infos = [AttributeInfo(
            **value.data) for value in self.attribute_infos]
        self_query_retriever = SelfQueryRetriever.from_llm(
            llm=self.llm,
            vectorstore=self.vectorstore,
            document_contents=self.document_content_description,
            metadata_field_info=metadata_field_infos,
            enable_limit=True,
        )

        if isinstance(self.query, Message):
            input_text = self.query.text
        elif isinstance(self.query, str):
            input_text = self.query
        else:
            msg = f"Query type {type(self.query)} not supported."
            raise TypeError(msg)

        documents = self_query_retriever.invoke(
            input=input_text, config={"callbacks": self.get_langchain_callbacks()})
        data = [Data.from_document(document) for document in documents]
        self.status = data
        return data
