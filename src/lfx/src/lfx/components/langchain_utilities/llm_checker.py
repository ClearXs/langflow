import i18n
from langchain.chains import LLMCheckerChain

from lfx.base.chains.model import LCChainComponent
from lfx.inputs.inputs import HandleInput, MultilineInput
from lfx.schema import Message


class LLMCheckerChainComponent(LCChainComponent):
    display_name = i18n.t(
        'components.langchain_utilities.llm_checker.display_name')
    description = i18n.t(
        'components.langchain_utilities.llm_checker.description')
    documentation = "https://python.langchain.com/docs/modules/chains/additional/llm_checker"
    name = "LLMCheckerChain"
    legacy: bool = True
    icon = "LangChain"
    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.langchain_utilities.llm_checker.input_value.display_name'),
            info=i18n.t(
                'components.langchain_utilities.llm_checker.input_value.info'),
            required=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.llm_checker.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
        ),
    ]

    def invoke_chain(self) -> Message:
        chain = LLMCheckerChain.from_llm(llm=self.llm)
        response = chain.invoke(
            {chain.input_key: self.input_value},
            config={"callbacks": self.get_langchain_callbacks()},
        )
        result = response.get(chain.output_key, "")
        result = str(result)
        self.status = result
        return Message(text=result)
