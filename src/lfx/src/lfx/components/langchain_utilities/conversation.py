import i18n
from lfx.base.chains.model import LCChainComponent
from lfx.inputs.inputs import HandleInput, MultilineInput
from lfx.schema.message import Message


class ConversationChainComponent(LCChainComponent):
    display_name = i18n.t(
        'components.langchain_utilities.conversation.display_name')
    description = i18n.t(
        'components.langchain_utilities.conversation.description')
    name = "ConversationChain"
    legacy: bool = True
    icon = "LangChain"

    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.langchain_utilities.conversation.input_value.display_name'),
            info=i18n.t(
                'components.langchain_utilities.conversation.input_value.info'),
            required=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.conversation.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
        ),
        HandleInput(
            name="memory",
            display_name=i18n.t(
                'components.langchain_utilities.conversation.memory.display_name'),
            input_types=["BaseChatMemory"],
        ),
    ]

    def invoke_chain(self) -> Message:
        try:
            from langchain.chains import ConversationChain
        except ImportError as e:
            msg = (
                "ConversationChain requires langchain to be installed. Please install it with "
                "`uv pip install langchain`."
            )
            raise ImportError(msg) from e

        if not self.memory:
            chain = ConversationChain(llm=self.llm)
        else:
            chain = ConversationChain(llm=self.llm, memory=self.memory)

        result = chain.invoke(
            {"input": self.input_value},
            config={"callbacks": self.get_langchain_callbacks()},
        )
        if isinstance(result, dict):
            result = result.get(chain.output_key, "")

        elif not isinstance(result, str):
            result = result.get("response")
        result = str(result)
        self.status = result
        return Message(text=result)
