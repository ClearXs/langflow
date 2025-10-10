import os
import i18n
from lfx.base.models.aws_constants import AWS_REGIONS, AWS_MODEL_IDs
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.inputs.inputs import MessageTextInput, SecretStrInput
from lfx.io import DictInput, DropdownInput
from lfx.log.logger import logger


class AmazonBedrockComponent(LCModelComponent):
    display_name: str = i18n.t(
        'components.amazon.amazon_bedrock_model.display_name')
    description: str = i18n.t(
        'components.amazon.amazon_bedrock_model.description')
    icon = "Amazon"
    name = "AmazonBedrockModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="model_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.model_id.display_name'),
            options=AWS_MODEL_IDs,
            value="anthropic.claude-3-haiku-20240307-v1:0",
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.model_id.info'),
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_access_key_id.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_access_key_id.info'),
            value="AWS_ACCESS_KEY_ID",
            required=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_secret_access_key.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_secret_access_key.info'),
            value="AWS_SECRET_ACCESS_KEY",
            required=True,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_session_token.display_name'),
            advanced=False,
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.aws_session_token.info'),
            load_from_db=False,
        ),
        SecretStrInput(
            name="credentials_profile_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.credentials_profile_name.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.credentials_profile_name.info'),
            load_from_db=False,
        ),
        DropdownInput(
            name="region_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.region_name.display_name'),
            value="us-east-1",
            options=AWS_REGIONS,
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.region_name.info'),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.model_kwargs.display_name'),
            advanced=True,
            is_list=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.model_kwargs.info'),
        ),
        MessageTextInput(
            name="endpoint_url",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_model.endpoint_url.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_model.endpoint_url.info'),
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build and return the Amazon Bedrock model."""
        try:
            # Import required libraries
            try:
                from langchain_aws import ChatBedrock
            except ImportError as e:
                error_msg = i18n.t(
                    'components.amazon.amazon_bedrock_model.errors.langchain_aws_not_installed')
                raise ImportError(error_msg) from e

            try:
                import boto3
            except ImportError as e:
                error_msg = i18n.t(
                    'components.amazon.amazon_bedrock_model.errors.boto3_not_installed')
                raise ImportError(error_msg) from e

            self.status = i18n.t(
                'components.amazon.amazon_bedrock_model.status.creating_session')

            # Create AWS session based on provided credentials
            try:
                if self.aws_access_key_id or self.aws_secret_access_key:
                    session = boto3.Session(
                        aws_access_key_id=self.aws_access_key_id,
                        aws_secret_access_key=self.aws_secret_access_key,
                        aws_session_token=self.aws_session_token,
                    )
                    logger.debug(
                        i18n.t('components.amazon.amazon_bedrock_model.logs.session_created_with_keys'))
                elif self.credentials_profile_name:
                    session = boto3.Session(
                        profile_name=self.credentials_profile_name)
                    logger.debug(i18n.t('components.amazon.amazon_bedrock_model.logs.session_created_with_profile',
                                        profile=self.credentials_profile_name))
                else:
                    session = boto3.Session()
                    logger.debug(
                        i18n.t('components.amazon.amazon_bedrock_model.logs.session_created_default'))

            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_model.errors.session_creation_failed',
                                   error=str(e))
                raise ValueError(error_msg) from e

            # Prepare client parameters
            client_params = {}
            if self.endpoint_url:
                client_params["endpoint_url"] = self.endpoint_url
                logger.debug(i18n.t('components.amazon.amazon_bedrock_model.logs.endpoint_url_set',
                                    url=self.endpoint_url))

            if self.region_name:
                client_params["region_name"] = self.region_name
                logger.debug(i18n.t('components.amazon.amazon_bedrock_model.logs.region_set',
                                    region=self.region_name))

            self.status = i18n.t(
                'components.amazon.amazon_bedrock_model.status.creating_client')

            try:
                boto3_client = session.client(
                    "bedrock-runtime", **client_params)
                logger.debug(
                    i18n.t('components.amazon.amazon_bedrock_model.logs.client_created'))
            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_model.errors.client_creation_failed',
                                   error=str(e))
                raise RuntimeError(error_msg) from e

            self.status = i18n.t('components.amazon.amazon_bedrock_model.status.initializing_model',
                                 model=self.model_id)

            try:
                output = ChatBedrock(
                    client=boto3_client,
                    model_id=self.model_id,
                    region_name=self.region_name,
                    model_kwargs=self.model_kwargs,
                    endpoint_url=self.endpoint_url,
                    streaming=self.stream,
                )

                success_msg = i18n.t('components.amazon.amazon_bedrock_model.success.model_initialized',
                                     model=self.model_id, region=self.region_name)
                logger.info(success_msg)
                self.status = success_msg

                return output

            except Exception as e:
                error_msg = i18n.t('components.amazon.amazon_bedrock_model.errors.model_connection_failed',
                                   error=str(e))
                raise ValueError(error_msg) from e

        except (ImportError, ValueError, RuntimeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t('components.amazon.amazon_bedrock_model.errors.model_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
