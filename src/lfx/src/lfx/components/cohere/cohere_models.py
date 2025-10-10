import os
import i18n
from langchain_cohere import ChatCohere
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import SecretStrInput, SliderInput
from lfx.log.logger import logger


class CohereComponent(LCModelComponent):
    display_name = i18n.t('components.cohere.cohere_models.display_name')
    description = i18n.t('components.cohere.cohere_models.description')
    documentation = "https://python.langchain.com/docs/integrations/llms/cohere/"
    icon = "Cohere"
    name = "CohereModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        SecretStrInput(
            name="cohere_api_key",
            display_name=i18n.t(
                'components.cohere.cohere_models.cohere_api_key.display_name'),
            info=i18n.t('components.cohere.cohere_models.cohere_api_key.info'),
            advanced=False,
            value="COHERE_API_KEY",
            required=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.cohere.cohere_models.temperature.display_name'),
            value=0.75,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            info=i18n.t('components.cohere.cohere_models.temperature.info'),
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        try:
            self.status = i18n.t(
                'components.cohere.cohere_models.status.initializing')
            logger.info(i18n.t('components.cohere.cohere_models.logs.initializing',
                               temperature=self.temperature))

            cohere_api_key = self.cohere_api_key
            temperature = self.temperature

            api_key = SecretStr(cohere_api_key).get_secret_value(
            ) if cohere_api_key else None

            model = ChatCohere(
                temperature=temperature or 0.75,
                cohere_api_key=api_key,
            )

            success_msg = i18n.t('components.cohere.cohere_models.success.model_created',
                                 temperature=temperature or 0.75)
            self.status = success_msg
            logger.info(success_msg)

            return model

        except Exception as e:
            error_msg = i18n.t('components.cohere.cohere_models.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
