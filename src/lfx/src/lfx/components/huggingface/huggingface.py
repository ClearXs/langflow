import i18n
from typing import Any

from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint
from tenacity import retry, stop_after_attempt, wait_fixed

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import DictInput, DropdownInput, FloatInput, IntInput, SecretStrInput, SliderInput, StrInput
from lfx.log.logger import logger

# TODO: langchain_community.llms.huggingface_endpoint is depreciated.
#  Need to update to langchain_huggingface, but have dependency with langchain_core 0.3.0

# Constants
DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


class HuggingFaceEndpointsComponent(LCModelComponent):
    display_name: str = "Hugging Face"
    description: str = i18n.t('components.huggingface.huggingface.description')
    icon = "HuggingFace"
    name = "HuggingFaceModel"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="model_id",
            display_name=i18n.t(
                'components.huggingface.huggingface.model_id.display_name'),
            info=i18n.t('components.huggingface.huggingface.model_id.info'),
            options=[
                DEFAULT_MODEL,
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "meta-llama/Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
                "Qwen/QwQ-32B-Preview",
                "openai-community/gpt2",
                "custom",
            ],
            value=DEFAULT_MODEL,
            required=True,
            real_time_refresh=True,
        ),
        StrInput(
            name="custom_model",
            display_name=i18n.t(
                'components.huggingface.huggingface.custom_model.display_name'),
            info=i18n.t(
                'components.huggingface.huggingface.custom_model.info'),
            value="",
            show=False,
            required=True,
        ),
        IntInput(
            name="max_new_tokens",
            display_name=i18n.t(
                'components.huggingface.huggingface.max_new_tokens.display_name'),
            value=512,
            info=i18n.t(
                'components.huggingface.huggingface.max_new_tokens.info')
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t(
                'components.huggingface.huggingface.top_k.display_name'),
            advanced=True,
            info=i18n.t('components.huggingface.huggingface.top_k.info'),
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.huggingface.huggingface.top_p.display_name'),
            value=0.95,
            advanced=True,
            info=i18n.t('components.huggingface.huggingface.top_p.info'),
        ),
        FloatInput(
            name="typical_p",
            display_name=i18n.t(
                'components.huggingface.huggingface.typical_p.display_name'),
            value=0.95,
            advanced=True,
            info=i18n.t('components.huggingface.huggingface.typical_p.info'),
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.huggingface.huggingface.temperature.display_name'),
            value=0.8,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            info=i18n.t('components.huggingface.huggingface.temperature.info'),
            advanced=True,
        ),
        FloatInput(
            name="repetition_penalty",
            display_name=i18n.t(
                'components.huggingface.huggingface.repetition_penalty.display_name'),
            info=i18n.t(
                'components.huggingface.huggingface.repetition_penalty.info'),
            advanced=True,
        ),
        StrInput(
            name="inference_endpoint",
            display_name=i18n.t(
                'components.huggingface.huggingface.inference_endpoint.display_name'),
            value="https://api-inference.huggingface.co/models/",
            info=i18n.t(
                'components.huggingface.huggingface.inference_endpoint.info'),
            required=True,
        ),
        DropdownInput(
            name="task",
            display_name=i18n.t(
                'components.huggingface.huggingface.task.display_name'),
            options=["text2text-generation", "text-generation",
                     "summarization", "translation"],
            value="text-generation",
            advanced=True,
            info=i18n.t('components.huggingface.huggingface.task.info'),
        ),
        SecretStrInput(
            name="huggingfacehub_api_token",
            display_name=i18n.t(
                'components.huggingface.huggingface.huggingfacehub_api_token.display_name'),
            password=True,
            required=True
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.huggingface.huggingface.model_kwargs.display_name'),
            advanced=True
        ),
        IntInput(
            name="retry_attempts",
            display_name=i18n.t(
                'components.huggingface.huggingface.retry_attempts.display_name'),
            value=1,
            advanced=True
        ),
    ]

    def get_api_url(self) -> str:
        """Get the API URL for the inference endpoint.

        Returns:
            str: The constructed API URL.

        Raises:
            ValueError: If custom model ID is required but not provided.
        """
        logger.debug(
            i18n.t('components.huggingface.huggingface.logs.getting_api_url'))

        if "huggingface" in self.inference_endpoint.lower():
            if self.model_id == "custom":
                if not self.custom_model:
                    error_msg = i18n.t(
                        'components.huggingface.huggingface.errors.custom_model_required')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                url = f"{self.inference_endpoint}{self.custom_model}"
                logger.debug(i18n.t('components.huggingface.huggingface.logs.using_custom_model',
                                    model=self.custom_model,
                                    url=url))
                return url

            url = f"{self.inference_endpoint}{self.model_id}"
            logger.debug(i18n.t('components.huggingface.huggingface.logs.using_standard_model',
                                model=self.model_id,
                                url=url))
            return url

        logger.debug(i18n.t('components.huggingface.huggingface.logs.using_custom_endpoint',
                            endpoint=self.inference_endpoint))
        return self.inference_endpoint

    async def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        """Update build configuration based on field updates.

        Args:
            build_config: The build configuration to update.
            field_value: The new field value.
            field_name: The name of the field that changed.

        Returns:
            dict: Updated build configuration.
        """
        try:
            if field_name is None or field_name == "model_id":
                logger.debug(i18n.t('components.huggingface.huggingface.logs.updating_config',
                                    field=field_name or 'model_id',
                                    value=field_value))

                # If model_id is custom, show custom model field
                if field_value == "custom":
                    logger.debug(
                        i18n.t('components.huggingface.huggingface.logs.showing_custom_field'))
                    build_config["custom_model"]["show"] = True
                    build_config["custom_model"]["required"] = True
                else:
                    logger.debug(
                        i18n.t('components.huggingface.huggingface.logs.hiding_custom_field'))
                    build_config["custom_model"]["show"] = False
                    build_config["custom_model"]["value"] = ""

        except (KeyError, AttributeError) as e:
            error_msg = i18n.t('components.huggingface.huggingface.errors.config_update_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.log(error_msg)

        return build_config

    def create_huggingface_endpoint(
        self,
        task: str | None,
        huggingfacehub_api_token: str | None,
        model_kwargs: dict[str, Any],
        max_new_tokens: int,
        top_k: int | None,
        top_p: float,
        typical_p: float | None,
        temperature: float | None,
        repetition_penalty: float | None,
    ) -> HuggingFaceEndpoint:
        """Create HuggingFace endpoint with retry logic.

        Args:
            task: The task type.
            huggingfacehub_api_token: API token for authentication.
            model_kwargs: Additional model arguments.
            max_new_tokens: Maximum number of new tokens.
            top_k: Top-k sampling parameter.
            top_p: Top-p sampling parameter.
            typical_p: Typical-p sampling parameter.
            temperature: Temperature for sampling.
            repetition_penalty: Repetition penalty factor.

        Returns:
            HuggingFaceEndpoint: Configured endpoint instance.
        """
        retry_attempts = self.retry_attempts
        endpoint_url = self.get_api_url()

        logger.info(i18n.t('components.huggingface.huggingface.logs.creating_endpoint',
                           url=endpoint_url,
                           task=task or 'text-generation',
                           retry_attempts=retry_attempts))

        @retry(stop=stop_after_attempt(retry_attempts), wait=wait_fixed(2))
        def _attempt_create():
            logger.debug(
                i18n.t('components.huggingface.huggingface.logs.attempting_connection'))
            return HuggingFaceEndpoint(
                endpoint_url=endpoint_url,
                task=task,
                huggingfacehub_api_token=huggingfacehub_api_token,
                model_kwargs=model_kwargs,
                max_new_tokens=max_new_tokens,
                top_k=top_k,
                top_p=top_p,
                typical_p=typical_p,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
            )

        return _attempt_create()

    def build_model(self) -> LanguageModel:
        """Build HuggingFace language model.

        Returns:
            LanguageModel: Configured language model instance.

        Raises:
            ValueError: If connection to HuggingFace API fails.
        """
        logger.info(
            i18n.t('components.huggingface.huggingface.logs.building_model'))

        task = self.task or None
        huggingfacehub_api_token = self.huggingfacehub_api_token
        model_kwargs = self.model_kwargs or {}
        max_new_tokens = self.max_new_tokens
        top_k = self.top_k or None
        top_p = self.top_p
        typical_p = self.typical_p or None
        temperature = self.temperature or 0.8
        repetition_penalty = self.repetition_penalty or None

        logger.debug(i18n.t('components.huggingface.huggingface.logs.model_parameters',
                            task=task or 'text-generation',
                            max_tokens=max_new_tokens,
                            temperature=temperature,
                            top_k=top_k or 'default',
                            top_p=top_p,
                            typical_p=typical_p or 'default',
                            repetition_penalty=repetition_penalty or 'default'))

        try:
            llm = self.create_huggingface_endpoint(
                task=task,
                huggingfacehub_api_token=huggingfacehub_api_token,
                model_kwargs=model_kwargs,
                max_new_tokens=max_new_tokens,
                top_k=top_k,
                top_p=top_p,
                typical_p=typical_p,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
            )
            logger.info(
                i18n.t('components.huggingface.huggingface.logs.model_built'))
            return llm

        except Exception as e:
            error_msg = i18n.t('components.huggingface.huggingface.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
