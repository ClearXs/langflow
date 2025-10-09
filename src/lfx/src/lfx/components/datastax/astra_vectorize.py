from typing import Any

import i18n
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DictInput, DropdownInput, MessageTextInput, SecretStrInput
from lfx.log.logger import logger
from lfx.template.field.base import Output


class AstraVectorizeComponent(Component):
    display_name: str = i18n.t(
        'components.datastax.astra_vectorize.display_name')
    description: str = i18n.t(
        'components.datastax.astra_vectorize.description')
    documentation: str = "https://docs.datastax.com/en/astra-db-serverless/databases/embedding-generation.html"
    legacy = True
    icon = "AstraDB"
    name = "AstraVectorize"
    replacement = ["datastax.AstraDB"]

    VECTORIZE_PROVIDERS_MAPPING = {
        "Azure OpenAI": ["azureOpenAI", ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]],
        "Hugging Face - Dedicated": ["huggingfaceDedicated", ["endpoint-defined-model"]],
        "Hugging Face - Serverless": [
            "huggingface",
            [
                "sentence-transformers/all-MiniLM-L6-v2",
                "intfloat/multilingual-e5-large",
                "intfloat/multilingual-e5-large-instruct",
                "BAAI/bge-small-en-v1.5",
                "BAAI/bge-base-en-v1.5",
                "BAAI/bge-large-en-v1.5",
            ],
        ],
        "Jina AI": [
            "jinaAI",
            [
                "jina-embeddings-v2-base-en",
                "jina-embeddings-v2-base-de",
                "jina-embeddings-v2-base-es",
                "jina-embeddings-v2-base-code",
                "jina-embeddings-v2-base-zh",
            ],
        ],
        "Mistral AI": ["mistral", ["mistral-embed"]],
        "NVIDIA": ["nvidia", ["NV-Embed-QA"]],
        "OpenAI": ["openai", ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]],
        "Upstage": ["upstageAI", ["solar-embedding-1-large"]],
        "Voyage AI": [
            "voyageAI",
            ["voyage-large-2-instruct", "voyage-law-2",
                "voyage-code-2", "voyage-large-2", "voyage-2"],
        ],
    }
    VECTORIZE_MODELS_STR = "\n\n".join(
        [provider + ": " + (", ".join(models[1]))
         for provider, models in VECTORIZE_PROVIDERS_MAPPING.items()]
    )

    inputs = [
        DropdownInput(
            name="provider",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.provider.display_name'),
            options=VECTORIZE_PROVIDERS_MAPPING.keys(),
            value="",
            required=True,
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.model_name.display_name'),
            info=i18n.t('components.datastax.astra_vectorize.model_name.info',
                        models_list=VECTORIZE_MODELS_STR),
            required=True,
        ),
        MessageTextInput(
            name="api_key_name",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.api_key_name.display_name'),
            info=i18n.t(
                'components.datastax.astra_vectorize.api_key_name.info'),
        ),
        DictInput(
            name="authentication",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.authentication.display_name'),
            is_list=True,
            advanced=True,
        ),
        SecretStrInput(
            name="provider_api_key",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.provider_api_key.display_name'),
            info=i18n.t(
                'components.datastax.astra_vectorize.provider_api_key.info'),
            advanced=True,
        ),
        DictInput(
            name="model_parameters",
            display_name=i18n.t(
                'components.datastax.astra_vectorize.model_parameters.display_name'),
            advanced=True,
            is_list=True,
        ),
    ]
    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.astra_vectorize.outputs.config.display_name'),
            name="config",
            method="build_options",
            types=["dict"]
        ),
    ]

    def build_options(self) -> dict[str, Any]:
        """Build Astra Vectorize configuration options.

        Returns:
            dict[str, Any]: Configuration dictionary for Astra Vectorize.

        Raises:
            ValueError: If configuration build fails.
        """
        try:
            logger.info(i18n.t('components.datastax.astra_vectorize.logs.building_config',
                               provider=self.provider,
                               model=self.model_name))
            self.status = i18n.t(
                'components.datastax.astra_vectorize.status.building')

            provider_value = self.VECTORIZE_PROVIDERS_MAPPING[self.provider][0]
            logger.debug(i18n.t('components.datastax.astra_vectorize.logs.provider_mapped',
                                provider=self.provider,
                                provider_value=provider_value))

            authentication = {**(self.authentication or {})}
            api_key_name = self.api_key_name

            if api_key_name:
                authentication["providerKey"] = api_key_name
                logger.debug(i18n.t('components.datastax.astra_vectorize.logs.api_key_name_set',
                                    key_name=api_key_name))

            config = {
                # must match astrapy.info.VectorServiceOptions
                "collection_vector_service_options": {
                    "provider": provider_value,
                    "modelName": self.model_name,
                    "authentication": authentication,
                    "parameters": self.model_parameters or {},
                },
                "collection_embedding_api_key": self.provider_api_key,
            }

            success_msg = i18n.t('components.datastax.astra_vectorize.status.config_created',
                                 provider=self.provider,
                                 model=self.model_name)
            self.status = success_msg
            logger.info(success_msg)

            return config

        except Exception as e:
            error_msg = i18n.t('components.datastax.astra_vectorize.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
