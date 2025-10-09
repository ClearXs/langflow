import i18n
from langchain.agents import AgentExecutor, create_vectorstore_router_agent
from langchain.agents.agent_toolkits.vectorstore.toolkit import VectorStoreRouterToolkit

from lfx.base.agents.agent import LCAgentComponent
from lfx.inputs.inputs import HandleInput


class VectorStoreRouterAgentComponent(LCAgentComponent):
    display_name = i18n.t(
        'components.langchain_utilities.vector_store_router.display_name')
    description = i18n.t(
        'components.langchain_utilities.vector_store_router.description')
    name = "VectorStoreRouterAgent"
    legacy: bool = True
    icon = "LangChain"

    inputs = [
        *LCAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_router.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
            info=i18n.t(
                'components.langchain_utilities.vector_store_router.llm.info'),
        ),
        HandleInput(
            name="vectorstores",
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_router.vectorstores.display_name'),
            input_types=["VectorStoreInfo"],
            is_list=True,
            required=True,
            info=i18n.t(
                'components.langchain_utilities.vector_store_router.vectorstores.info'),
        ),
    ]

    def build_agent(self) -> AgentExecutor:
        toolkit = VectorStoreRouterToolkit(
            vectorstores=self.vectorstores, llm=self.llm)
        return create_vectorstore_router_agent(llm=self.llm, toolkit=toolkit, **self.get_agent_kwargs())
