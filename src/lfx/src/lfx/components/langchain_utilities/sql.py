import i18n
from langchain.agents import AgentExecutor
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase

from lfx.base.agents.agent import LCAgentComponent
from lfx.inputs.inputs import HandleInput, MessageTextInput
from lfx.io import Output


class SQLAgentComponent(LCAgentComponent):
    display_name = i18n.t('components.langchain_utilities.sql.display_name')
    description = i18n.t('components.langchain_utilities.sql.description')
    name = "SQLAgent"
    icon = "LangChain"
    inputs = [
        *LCAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.sql.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
            info=i18n.t('components.langchain_utilities.sql.llm.info'),
        ),
        MessageTextInput(
            name="database_uri",
            display_name=i18n.t(
                'components.langchain_utilities.sql.database_uri.display_name'),
            required=True,
            info=i18n.t(
                'components.langchain_utilities.sql.database_uri.info'),
        ),
        HandleInput(
            name="extra_tools",
            display_name=i18n.t(
                'components.langchain_utilities.sql.extra_tools.display_name'),
            input_types=["Tool"],
            is_list=True,
            advanced=True,
            info=i18n.t('components.langchain_utilities.sql.extra_tools.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.sql.outputs.response.display_name'),
            name="response",
            method="message_response"
        ),
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.sql.outputs.agent.display_name'),
            name="agent",
            method="build_agent",
            tool_mode=False
        ),
    ]

    def build_agent(self) -> AgentExecutor:
        db = SQLDatabase.from_uri(self.database_uri)
        toolkit = SQLDatabaseToolkit(db=db, llm=self.llm)
        agent_args = self.get_agent_kwargs()
        agent_args["max_iterations"] = agent_args["agent_executor_kwargs"]["max_iterations"]
        del agent_args["agent_executor_kwargs"]["max_iterations"]
        return create_sql_agent(llm=self.llm, toolkit=toolkit, extra_tools=self.extra_tools or [], **agent_args)
