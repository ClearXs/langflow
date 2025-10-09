import i18n
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from lfx.base.agents.agent import LCToolsAgentComponent
from lfx.inputs.inputs import (
    DataInput,
    HandleInput,
    MessageTextInput,
)
from lfx.schema.data import Data


class ToolCallingAgentComponent(LCToolsAgentComponent):
    display_name: str = i18n.t(
        'components.langchain_utilities.tool_calling.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.tool_calling.description')
    icon = "LangChain"
    name = "ToolCallingAgent"

    inputs = [
        *LCToolsAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.tool_calling.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
            info=i18n.t(
                'components.langchain_utilities.tool_calling.llm.info'),
        ),
        MessageTextInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.langchain_utilities.tool_calling.system_prompt.display_name'),
            info=i18n.t(
                'components.langchain_utilities.tool_calling.system_prompt.info'),
            value="You are a helpful assistant that can use tools to answer questions and perform tasks.",
        ),
        DataInput(
            name="chat_history",
            display_name=i18n.t(
                'components.langchain_utilities.tool_calling.chat_history.display_name'),
            is_list=True,
            advanced=True,
            info=i18n.t(
                'components.langchain_utilities.tool_calling.chat_history.info'),
        ),
    ]

    def get_chat_history_data(self) -> list[Data] | None:
        return self.chat_history

    def create_agent_runnable(self):
        messages = [
            ("system", "{system_prompt}"),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        self.validate_tool_names()
        try:
            return create_tool_calling_agent(self.llm, self.tools or [], prompt)
        except NotImplementedError as e:
            message = f"{self.display_name} does not support tool calling. Please try using a compatible model."
            raise NotImplementedError(message) from e
