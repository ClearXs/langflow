import i18n
from typing import cast

from langchain.chains import RetrievalQA

from lfx.base.chains.model import LCChainComponent
from lfx.inputs.inputs import BoolInput, DropdownInput, HandleInput, MultilineInput
from lfx.schema import Message


class RetrievalQAComponent(LCChainComponent):
    display_name = i18n.t(
        'components.langchain_utilities.retrieval_qa.display_name')
    description = i18n.t(
        'components.langchain_utilities.retrieval_qa.description')
    name = "RetrievalQA"
    legacy: bool = True
    icon = "LangChain"
    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.input_value.display_name'),
            info=i18n.t(
                'components.langchain_utilities.retrieval_qa.input_value.info'),
            required=True,
        ),
        DropdownInput(
            name="chain_type",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.chain_type.display_name'),
            info=i18n.t(
                'components.langchain_utilities.retrieval_qa.chain_type.info'),
            options=["Stuff", "Map Reduce", "Refine", "Map Rerank"],
            value="Stuff",
            advanced=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
        ),
        HandleInput(
            name="retriever",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.retriever.display_name'),
            input_types=["Retriever"],
            required=True,
        ),
        HandleInput(
            name="memory",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.memory.display_name'),
            input_types=["BaseChatMemory"],
        ),
        BoolInput(
            name="return_source_documents",
            display_name=i18n.t(
                'components.langchain_utilities.retrieval_qa.return_source_documents.display_name'),
            value=False,
        ),
    ]

    def invoke_chain(self) -> Message:
        chain_type = self.chain_type.lower().replace(" ", "_")
        if self.memory:
            self.memory.input_key = "query"
            self.memory.output_key = "result"

        runnable = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type=chain_type,
            retriever=self.retriever,
            memory=self.memory,
            # always include to help debugging
            #
            return_source_documents=True,
        )

        result = runnable.invoke(
            {"query": self.input_value},
            config={"callbacks": self.get_langchain_callbacks()},
        )

        source_docs = self.to_data(result.get("source_documents", keys=[]))
        result_str = str(result.get("result", ""))
        if self.return_source_documents and len(source_docs):
            references_str = self.create_references_from_data(source_docs)
            result_str = f"{result_str}\n{references_str}"
        # put the entire result to debug history, query and content
        self.status = {
            **result, "source_documents": source_docs, "output": result_str}
        return cast("Message", result_str)
