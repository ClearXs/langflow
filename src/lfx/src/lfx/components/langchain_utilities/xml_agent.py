import i18n
from langchain.agents import create_xml_agent
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, PromptTemplate

from lfx.base.agents.agent import LCToolsAgentComponent
from lfx.inputs.inputs import (
    DataInput,
    HandleInput,
    MultilineInput,
)
from lfx.schema.data import Data


class XMLAgentComponent(LCToolsAgentComponent):
    display_name: str = i18n.t(
        'components.langchain_utilities.xml_agent.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.xml_agent.description')
    icon = "LangChain"
    beta = True
    name = "XMLAgent"
    inputs = [
        *LCToolsAgentComponent.get_base_inputs(),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.xml_agent.llm.display_name'),
            input_types=["LanguageModel"],
            required=True
        ),
        DataInput(
            name="chat_history",
            display_name=i18n.t(
                'components.langchain_utilities.xml_agent.chat_history.display_name'),
            is_list=True,
            advanced=True
        ),
        MultilineInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.langchain_utilities.xml_agent.system_prompt.display_name'),
            info=i18n.t(
                'components.langchain_utilities.xml_agent.system_prompt.info'),
            value="""You are a helpful assistant. Help the user answer any questions.

You have access to the following tools:

{tools}

In order to use a tool, you can use <tool></tool> and <tool_input></tool_input> tags. You will then get back a response in the form <observation></observation>

For example, if you have a tool called 'search' that could run a google search, in order to search for the weather in SF you would respond:

<tool>search</tool><tool_input>weather in SF</tool_input>

<observation>64 degrees</observation>

When you are done, respond with a final answer between <final_answer></final_answer>. For example:

<final_answer>The weather in SF is 64 degrees</final_answer>

Begin!

Question: {input}

{agent_scratchpad}
            """,  # noqa: E501
        ),
        MultilineInput(
            name="user_prompt",
            display_name=i18n.t(
                'components.langchain_utilities.xml_agent.user_prompt.display_name'),
            info=i18n.t(
                'components.langchain_utilities.xml_agent.user_prompt.info'),
            value="{input}"
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
            ("ai", "{agent_scratchpad}"),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        return create_xml_agent(self.llm, self.tools, prompt)
