import i18n
from langchain_experimental.agents.agent_toolkits.csv.base import create_csv_agent

from lfx.base.agents.agent import LCAgentComponent
from lfx.field_typing import AgentExecutor
from lfx.inputs.inputs import (
    DictInput,
    DropdownInput,
    FileInput,
    HandleInput,
    MessageTextInput,
)
from lfx.schema.message import Message
from lfx.template.field.base import Output


class CSVAgentComponent(LCAgentComponent):
    display_name = i18n.t(
        'components.langchain_utilities.csv_agent.display_name')
    description = i18n.t(
        'components.langchain_utilities.csv_agent.description')
    documentation = "https://python.langchain.com/docs/modules/agents/toolkits/csv"
    name = "CSVAgent"
    icon = "LangChain"

    inputs = [
        *LCAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
            info=i18n.t('components.langchain_utilities.csv_agent.llm.info'),
        ),
        FileInput(
            name="path",
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.path.display_name'),
            file_types=["csv"],
            input_types=["str", "Message"],
            required=True,
            info=i18n.t('components.langchain_utilities.csv_agent.path.info'),
        ),
        DropdownInput(
            name="agent_type",
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.agent_type.display_name'),
            advanced=True,
            options=["zero-shot-react-description",
                     "openai-functions", "openai-tools"],
            value="openai-tools",
        ),
        MessageTextInput(
            name="input_value",
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.input_value.display_name'),
            info=i18n.t(
                'components.langchain_utilities.csv_agent.input_value.info'),
            required=True,
        ),
        DictInput(
            name="pandas_kwargs",
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.pandas_kwargs.display_name'),
            info=i18n.t(
                'components.langchain_utilities.csv_agent.pandas_kwargs.info'),
            advanced=True,
            is_list=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.outputs.response.display_name'),
            name="response",
            method="build_agent_response"
        ),
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.csv_agent.outputs.agent.display_name'),
            name="agent",
            method="build_agent",
            hidden=True,
            tool_mode=False
        ),
    ]

    def _path(self) -> str:
        if isinstance(self.path, Message) and isinstance(self.path.text, str):
            return self.path.text
        return self.path

    def build_agent_response(self) -> Message:
        agent_kwargs = {
            "verbose": self.verbose,
            "allow_dangerous_code": True,
        }

        agent_csv = create_csv_agent(
            llm=self.llm,
            path=self._path(),
            agent_type=self.agent_type,
            handle_parsing_errors=self.handle_parsing_errors,
            pandas_kwargs=self.pandas_kwargs,
            **agent_kwargs,
        )

        result = agent_csv.invoke({"input": self.input_value})
        return Message(text=str(result["output"]))

    def build_agent(self) -> AgentExecutor:
        agent_kwargs = {
            "verbose": self.verbose,
            "allow_dangerous_code": True,
        }

        agent_csv = create_csv_agent(
            llm=self.llm,
            path=self._path(),
            agent_type=self.agent_type,
            handle_parsing_errors=self.handle_parsing_errors,
            pandas_kwargs=self.pandas_kwargs,
            **agent_kwargs,
        )

        self.status = Message(text=str(agent_csv))

        return agent_csv
