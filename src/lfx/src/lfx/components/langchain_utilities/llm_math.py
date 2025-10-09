import i18n
from langchain.chains import LLMMathChain

from lfx.base.chains.model import LCChainComponent
from lfx.inputs.inputs import HandleInput, MultilineInput
from lfx.schema import Message
from lfx.template.field.base import Output


class LLMMathChainComponent(LCChainComponent):
    display_name = i18n.t(
        'components.langchain_utilities.llm_math.display_name')
    description = i18n.t('components.langchain_utilities.llm_math.description')
    documentation = "https://python.langchain.com/docs/modules/chains/additional/llm_math"
    name = "LLMMathChain"
    legacy: bool = True
    icon = "LangChain"
    inputs = [
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.langchain_utilities.llm_math.input_value.display_name'),
            info=i18n.t(
                'components.langchain_utilities.llm_math.input_value.info'),
            required=True,
        ),
        HandleInput(
            name="llm",
            display_name=i18n.t(
                'components.langchain_utilities.llm_math.llm.display_name'),
            input_types=["LanguageModel"],
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.llm_math.outputs.text.display_name'),
            name="text",
            method="invoke_chain"
        )
    ]

    def invoke_chain(self) -> Message:
        chain = LLMMathChain.from_llm(llm=self.llm)
        response = chain.invoke(
            {chain.input_key: self.input_value},
            config={"callbacks": self.get_langchain_callbacks()},
        )
        result = response.get(chain.output_key, "")
        result = str(result)
        self.status = result
        return Message(text=result)
