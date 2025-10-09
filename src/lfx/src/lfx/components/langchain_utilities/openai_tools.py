import i18n
from langchain.agents import create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, PromptTemplate

from lfx.base.agents.agent import LCToolsAgentComponent
from lfx.inputs.inputs import (
    DataInput,
    HandleInput,
    MultilineInput,
)
from lfx.schema.data import Data


class OpenAIToolsAgentComponent(LCToolsAgentComponent):
    display_name: str = i18n.t(
        'components.langchain_utilities.openai_tools.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.openai_tools.description')
    icon = "LangChain"
    name = "OpenAIToolsAgent"

    inputs = [
        *LCToolsAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.openai_tools.llm.display_name'),
            input_types=["LanguageModel", "ToolEnabledLanguageModel"],
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.langchain_utilities.openai_tools.system_prompt.display_name'),
            info=i18n.t(
                'components.langchain_utilities.openai_tools.system_prompt.info'),
            value="You are a helpful assistant",
        ),
        MultilineInput(
            name="user_prompt",
            display_name=i18n.t(
                'components.langchain_utilities.openai_tools.user_prompt.display_name'),
            info=i18n.t(
                'components.langchain_utilities.openai_tools.user_prompt.info'),
            value="{input}"
        ),
        DataInput(
            name="chat_history",
            display_name=i18n.t(
                'components.langchain_utilities.openai_tools.chat_history.display_name'),
            is_list=True,
            advanced=True
        ),
    ]

    def get_chat_history_data(self) -> list[Data] | None:
        return self.chat_history

    def create_agent_runnable(self):
        if "input" not in self.user_prompt:
            msg = "Prompt must contain 'input' key."
            raise ValueError(msg)
        messages = [
            ("system", self.system_prompt),
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate(prompt=PromptTemplate(
                input_variables=["input"], template=self.user_prompt)),
            ("placeholder", "{agent_scratchpad}"),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        return create_openai_tools_agent(self.llm, self.tools, prompt)
