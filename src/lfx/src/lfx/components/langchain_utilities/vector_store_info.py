import i18n
from langchain.agents.agent_toolkits.vectorstore.toolkit import VectorStoreInfo

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput, MessageTextInput, MultilineInput
from lfx.template.field.base import Output


class VectorStoreInfoComponent(Component):
    display_name = i18n.t(
        'components.langchain_utilities.vector_store_info.display_name')
    description = i18n.t(
        'components.langchain_utilities.vector_store_info.description')
    name = "VectorStoreInfo"
    legacy: bool = True
    icon = "LangChain"

    inputs = [
        MessageTextInput(
            name="vectorstore_name",
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_info.vectorstore_name.display_name'),
            info=i18n.t(
                'components.langchain_utilities.vector_store_info.vectorstore_name.info'),
            required=True,
        ),
        MultilineInput(
            name="vectorstore_description",
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_info.vectorstore_description.display_name'),
            info=i18n.t(
                'components.langchain_utilities.vector_store_info.vectorstore_description.info'),
            required=True,
        ),
        HandleInput(
            name="input_vectorstore",
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_info.input_vectorstore.display_name'),
            input_types=["VectorStore"],
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.vector_store_info.outputs.info.display_name'),
            name="info",
            method="build_info"
        ),
    ]

    def build_info(self) -> VectorStoreInfo:
        self.status = {
            "name": self.vectorstore_name,
            "description": self.vectorstore_description,
        }
        return VectorStoreInfo(
            vectorstore=self.input_vectorstore,
            description=self.vectorstore_description,
            name=self.vectorstore_name,
        )
