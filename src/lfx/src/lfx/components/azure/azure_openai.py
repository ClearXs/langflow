import i18n
from langchain_openai import AzureChatOpenAI

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import MessageTextInput
from lfx.io import DropdownInput, IntInput, SecretStrInput, SliderInput
from lfx.log.logger import logger


class AzureChatOpenAIComponent(LCModelComponent):
    display_name: str = i18n.t('components.azure.azure_openai.display_name')
    description: str = i18n.t('components.azure.azure_openai.description')
    documentation: str = "https://python.langchain.com/docs/integrations/llms/azure_openai"
    beta = False
    icon = "Azure"
    name = "AzureOpenAIModel"

    AZURE_OPENAI_API_VERSIONS = [
        "2024-06-01",
        "2024-07-01-preview",
        "2024-08-01-preview",
        "2024-09-01-preview",
        "2024-10-01-preview",
        "2023-05-15",
        "2023-12-01-preview",
        "2024-02-15-preview",
        "2024-03-01-preview",
        "2024-12-01-preview",
        "2025-01-01-preview",
        "2025-02-01-preview",
    ]

    inputs = [
        *LCModelComponent.get_base_inputs(),
        MessageTextInput(
            name="azure_endpoint",
            display_name=i18n.t(
                'components.azure.azure_openai.azure_endpoint.display_name'),
            info=i18n.t('components.azure.azure_openai.azure_endpoint.info'),
            required=True,
        ),
        MessageTextInput(
            name="azure_deployment",
            display_name=i18n.t(
                'components.azure.azure_openai.azure_deployment.display_name'),
            required=True,
            info=i18n.t('components.azure.azure_openai.azure_deployment.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.azure.azure_openai.api_key.display_name'),
            required=True,
            info=i18n.t('components.azure.azure_openai.api_key.info'),
        ),
        DropdownInput(
            name="api_version",
            display_name=i18n.t(
                'components.azure.azure_openai.api_version.display_name'),
            options=sorted(AZURE_OPENAI_API_VERSIONS, reverse=True),
            value=next(
                (
                    version
                    for version in sorted(AZURE_OPENAI_API_VERSIONS, reverse=True)
                    if not version.endswith("-preview")
                ),
                AZURE_OPENAI_API_VERSIONS[0],
            ),
            info=i18n.t('components.azure.azure_openai.api_version.info'),
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.azure.azure_openai.temperature.display_name'),
            value=0.7,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            info=i18n.t('components.azure.azure_openai.temperature.info'),
            advanced=True,
        ),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.azure.azure_openai.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.azure.azure_openai.max_tokens.info'),
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build Azure OpenAI chat model."""
        try:
            self.status = i18n.t('components.azure.azure_openai.status.initializing',
                                 deployment=self.azure_deployment)

            logger.debug(i18n.t('components.azure.azure_openai.logs.building_model',
                                endpoint=self.azure_endpoint,
                                deployment=self.azure_deployment,
                                api_version=self.api_version,
                                temperature=self.temperature,
                                max_tokens=self.max_tokens,
                                stream=self.stream))

            output = AzureChatOpenAI(
                azure_endpoint=self.azure_endpoint,
                azure_deployment=self.azure_deployment,
                api_version=self.api_version,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens or None,
                streaming=self.stream,
            )

            success_msg = i18n.t('components.azure.azure_openai.success.model_initialized',
                                 deployment=self.azure_deployment)
            logger.info(success_msg)
            self.status = success_msg

            return output

        except Exception as e:
            error_msg = i18n.t('components.azure.azure_openai.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
