import i18n
from urllib.parse import urlparse

import requests
from langchain_community.embeddings.huggingface import HuggingFaceInferenceAPIEmbeddings

# Next update: use langchain_huggingface
from pydantic import SecretStr
from tenacity import retry, stop_after_attempt, wait_fixed

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.field_typing import Embeddings
from lfx.io import MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger


class HuggingFaceInferenceAPIEmbeddingsComponent(LCEmbeddingsModel):
    display_name = "Hugging Face Embeddings Inference"
    description = i18n.t(
        'components.huggingface.huggingface_inference_api.description')
    documentation = "https://huggingface.co/docs/text-embeddings-inference/index"
    icon = "HuggingFace"
    name = "HuggingFaceInferenceAPIEmbeddings"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.huggingface.huggingface_inference_api.api_key.display_name'),
            advanced=False,
            info=i18n.t(
                'components.huggingface.huggingface_inference_api.api_key.info'),
        ),
        MessageTextInput(
            name="inference_endpoint",
            display_name=i18n.t(
                'components.huggingface.huggingface_inference_api.inference_endpoint.display_name'),
            required=True,
            value="https://api-inference.huggingface.co/models/",
            info=i18n.t(
                'components.huggingface.huggingface_inference_api.inference_endpoint.info'),
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.huggingface.huggingface_inference_api.model_name.display_name'),
            value="BAAI/bge-large-en-v1.5",
            info=i18n.t(
                'components.huggingface.huggingface_inference_api.model_name.info'),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.huggingface.huggingface_inference_api.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def validate_inference_endpoint(self, inference_endpoint: str) -> bool:
        """Validate the inference endpoint URL.

        Args:
            inference_endpoint: URL of the inference endpoint.

        Returns:
            bool: True if validation succeeds.

        Raises:
            ValueError: If URL format is invalid or endpoint is not responding.
        """
        logger.debug(i18n.t('components.huggingface.huggingface_inference_api.logs.validating_endpoint',
                            endpoint=inference_endpoint))

        parsed_url = urlparse(inference_endpoint)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            error_msg = i18n.t('components.huggingface.huggingface_inference_api.errors.invalid_url_format',
                               endpoint=self.inference_endpoint)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(i18n.t('components.huggingface.huggingface_inference_api.logs.checking_health',
                            endpoint=inference_endpoint))

        try:
            response = requests.get(f"{inference_endpoint}/health", timeout=5)
        except requests.RequestException as e:
            error_msg = i18n.t('components.huggingface.huggingface_inference_api.errors.endpoint_not_responding',
                               endpoint=inference_endpoint)
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        if response.status_code != requests.codes.ok:
            error_msg = i18n.t('components.huggingface.huggingface_inference_api.errors.health_check_failed',
                               status=response.status_code)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t(
            'components.huggingface.huggingface_inference_api.logs.endpoint_validated'))
        return True

    def get_api_url(self) -> str:
        """Get the API URL for the inference endpoint.

        Returns:
            str: The API URL.
        """
        logger.debug(
            i18n.t('components.huggingface.huggingface_inference_api.logs.getting_api_url'))

        if "huggingface" in self.inference_endpoint.lower():
            logger.debug(i18n.t(
                'components.huggingface.huggingface_inference_api.logs.using_hf_endpoint'))
            return f"{self.inference_endpoint}"

        logger.debug(i18n.t(
            'components.huggingface.huggingface_inference_api.logs.using_custom_endpoint'))
        return self.inference_endpoint

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def create_huggingface_embeddings(
        self, api_key: SecretStr, api_url: str, model_name: str
    ) -> HuggingFaceInferenceAPIEmbeddings:
        """Create HuggingFace embeddings instance with retry logic.

        Args:
            api_key: API key for authentication.
            api_url: API endpoint URL.
            model_name: Name of the model to use.

        Returns:
            HuggingFaceInferenceAPIEmbeddings: Configured embeddings instance.
        """
        logger.debug(i18n.t('components.huggingface.huggingface_inference_api.logs.creating_embeddings',
                            model=model_name,
                            url=api_url))

        return HuggingFaceInferenceAPIEmbeddings(api_key=api_key, api_url=api_url, model_name=model_name)

    def build_embeddings(self) -> Embeddings:
        """Build HuggingFace embeddings instance.

        Returns:
            Embeddings: Configured embeddings instance.

        Raises:
            ValueError: If API key is missing for non-local endpoints or connection fails.
        """
        logger.info(i18n.t('components.huggingface.huggingface_inference_api.logs.building_embeddings',
                           model=self.model_name))

        api_url = self.get_api_url()

        is_local_url = (
            api_url.startswith(
                ("http://localhost", "http://127.0.0.1", "http://0.0.0.0", "http://docker"))
            or "huggingface.co" not in api_url.lower()
        )

        logger.debug(i18n.t('components.huggingface.huggingface_inference_api.logs.url_type_detected',
                            is_local=is_local_url,
                            url=api_url))

        if not self.api_key and is_local_url:
            logger.info(i18n.t(
                'components.huggingface.huggingface_inference_api.logs.using_local_deployment'))
            self.validate_inference_endpoint(api_url)
            api_key = SecretStr("APIKeyForLocalDeployment")
        elif not self.api_key:
            error_msg = i18n.t(
                'components.huggingface.huggingface_inference_api.errors.api_key_required')
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.debug(
                i18n.t('components.huggingface.huggingface_inference_api.logs.using_api_key'))
            api_key = SecretStr(self.api_key).get_secret_value()

        try:
            logger.debug(
                i18n.t('components.huggingface.huggingface_inference_api.logs.connecting'))
            embeddings = self.create_huggingface_embeddings(
                api_key, api_url, self.model_name)
            logger.info(i18n.t(
                'components.huggingface.huggingface_inference_api.logs.embeddings_built'))
            return embeddings
        except Exception as e:
            error_msg = i18n.t('components.huggingface.huggingface_inference_api.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
