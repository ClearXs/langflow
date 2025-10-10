import os
import i18n
from lfx.base.models.aws_constants import AWS_EMBEDDING_MODEL_IDS, AWS_REGIONS
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import Embeddings
from lfx.inputs.inputs import SecretStrInput
from lfx.io import DropdownInput, MessageTextInput, Output
from lfx.log.logger import logger


class AmazonBedrockEmbeddingsComponent(LCModelComponent):
    display_name: str = i18n.t(
        'components.amazon.amazon_bedrock_embedding.display_name')
    description: str = i18n.t(
        'components.amazon.amazon_bedrock_embedding.description')
    icon = "Amazon"
    name = "AmazonBedrockEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DropdownInput(
            name="model_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.model_id.display_name'),
            options=AWS_EMBEDDING_MODEL_IDS,
            value="amazon.titan-embed-text-v1",
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.model_id.info'),
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_access_key_id.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_access_key_id.info'),
            value="AWS_ACCESS_KEY_ID",
            required=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_secret_access_key.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_secret_access_key.info'),
            value="AWS_SECRET_ACCESS_KEY",
            required=True,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_session_token.display_name'),
            advanced=False,
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.aws_session_token.info'),
            value="AWS_SESSION_TOKEN",
        ),
        SecretStrInput(
            name="credentials_profile_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.credentials_profile_name.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.credentials_profile_name.info'),
            value="AWS_CREDENTIALS_PROFILE_NAME",
        ),
        DropdownInput(
            name="region_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.region_name.display_name'),
            value="us-east-1",
            options=AWS_REGIONS,
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.region_name.info'),
        ),
        MessageTextInput(
            name="endpoint_url",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.endpoint_url.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_embedding.endpoint_url.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_embedding.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        """Build and return Amazon Bedrock embeddings model."""
        try:
            # Import required libraries
            try:
                from langchain_aws import BedrockEmbeddings
            except ImportError as e:
                error_msg = i18n.t(
                    'components.amazon.amazon_bedrock_embedding.errors.langchain_aws_not_installed')
                raise ImportError(error_msg) from e

            try:
                import boto3
            except ImportError as e:
                error_msg = i18n.t(
                    'components.amazon.amazon_bedrock_embedding.errors.boto3_not_installed')
                raise ImportError(error_msg) from e

            self.status = i18n.t(
                'components.amazon.amazon_bedrock_embedding.status.creating_session')

            # Create AWS session based on provided credentials
            try:
                if self.aws_access_key_id or self.aws_secret_access_key:
                    session = boto3.Session(
                        aws_access_key_id=self.aws_access_key_id,
                        aws_secret_access_key=self.aws_secret_access_key,
                        aws_session_token=self.aws_session_token,
                    )
                    logger.debug(i18n.t(
                        'components.amazon.amazon_bedrock_embedding.logs.session_created_with_keys'))
                elif self.credentials_profile_name:
                    session = boto3.Session(
                        profile_name=self.credentials_profile_name)
                    logger.debug(i18n.t('components.amazon.amazon_bedrock_embedding.logs.session_created_with_profile',
                                        profile=self.credentials_profile_name))
                else:
                    session = boto3.Session()
                    logger.debug(i18n.t(
                        'components.amazon.amazon_bedrock_embedding.logs.session_created_default'))

            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_embedding.errors.session_creation_failed',
                                   error=str(e))
                raise ValueError(error_msg) from e

            # Prepare client parameters
            client_params = {}
            if self.endpoint_url:
                client_params["endpoint_url"] = self.endpoint_url
                logger.debug(i18n.t('components.amazon.amazon_bedrock_embedding.logs.endpoint_url_set',
                                    url=self.endpoint_url))

            if self.region_name:
                client_params["region_name"] = self.region_name
                logger.debug(i18n.t('components.amazon.amazon_bedrock_embedding.logs.region_set',
                                    region=self.region_name))

            self.status = i18n.t(
                'components.amazon.amazon_bedrock_embedding.status.creating_client')

            try:
                boto3_client = session.client(
                    "bedrock-runtime", **client_params)
                logger.debug(
                    i18n.t('components.amazon.amazon_bedrock_embedding.logs.client_created'))
            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_embedding.errors.client_creation_failed',
                                   error=str(e))
                raise RuntimeError(error_msg) from e

            self.status = i18n.t('components.amazon.amazon_bedrock_embedding.status.initializing_embeddings',
                                 model=self.model_id)

            try:
                embeddings = BedrockEmbeddings(
                    credentials_profile_name=self.credentials_profile_name,
                    client=boto3_client,
                    model_id=self.model_id,
                    endpoint_url=self.endpoint_url,
                    region_name=self.region_name,
                )

                success_msg = i18n.t('components.amazon.amazon_bedrock_embedding.success.embeddings_initialized',
                                     model=self.model_id, region=self.region_name)
                logger.info(success_msg)
                self.status = success_msg

                return embeddings

            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_embedding.errors.embeddings_initialization_failed',
                                   model=self.model_id, error=str(e))
                raise RuntimeError(error_msg) from e

        except (ImportError, ValueError, RuntimeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t('components.amazon.amazon_bedrock_embedding.errors.embeddings_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
