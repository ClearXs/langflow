import os
import i18n
from langflow.base.models.aws_constants import AWS_REGIONS, AWS_MODEL_IDs
from langflow.base.models.model import LCModelComponent
from langflow.field_typing import LanguageModel
from langflow.inputs.inputs import BoolInput, FloatInput, IntInput, MessageTextInput, SecretStrInput
from langflow.io import DictInput, DropdownInput
from langflow.log.logger import logger


class AmazonBedrockConverseComponent(LCModelComponent):
    display_name: str = i18n.t(
        'components.amazon.amazon_bedrock_converse.display_name')
    description: str = i18n.t(
        'components.amazon.amazon_bedrock_converse.description')
    icon = "Amazon"
    name = "AmazonBedrockConverseModel"
    beta = True

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent._base_inputs,
        DropdownInput(
            name="model_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.model_id.display_name'),
            options=AWS_MODEL_IDs,
            value="anthropic.claude-3-5-sonnet-20241022-v2:0",
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.model_id.info'),
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_access_key_id.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_access_key_id.info'),
            value="AWS_ACCESS_KEY_ID",
            required=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_secret_access_key.display_name'),
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_secret_access_key.info'),
            value="AWS_SECRET_ACCESS_KEY",
            required=True,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_session_token.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.aws_session_token.info'),
            load_from_db=False,
        ),
        SecretStrInput(
            name="credentials_profile_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.credentials_profile_name.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.credentials_profile_name.info'),
            load_from_db=False,
        ),
        DropdownInput(
            name="region_name",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.region_name.display_name'),
            value="us-east-1",
            options=AWS_REGIONS,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.region_name.info'),
        ),
        MessageTextInput(
            name="endpoint_url",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.endpoint_url.display_name'),
            advanced=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.endpoint_url.info'),
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.temperature.display_name'),
            value=0.7,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.temperature.info'),
            advanced=True,
        ),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.max_tokens.display_name'),
            value=4096,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.max_tokens.info'),
            advanced=True,
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.top_p.display_name'),
            value=0.9,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.top_p.info'),
            advanced=True,
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.top_k.display_name'),
            value=250,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.top_k.info'),
            advanced=True,
        ),
        BoolInput(
            name="disable_streaming",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.disable_streaming.display_name'),
            value=False,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.disable_streaming.info'),
            advanced=True,
        ),
        DictInput(
            name="additional_model_fields",
            display_name=i18n.t(
                'components.amazon.amazon_bedrock_converse.additional_model_fields.display_name'),
            advanced=True,
            is_list=True,
            info=i18n.t(
                'components.amazon.amazon_bedrock_converse.additional_model_fields.info'),
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build and return the Amazon Bedrock Converse model."""
        try:
            # Import required library
            try:
                from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
            except ImportError as e:
                error_msg = i18n.t(
                    'components.amazon.amazon_bedrock_converse.errors.langchain_aws_not_installed')
                raise ImportError(error_msg) from e

            self.status = i18n.t('components.amazon.amazon_bedrock_converse.status.initializing_model',
                                 model=self.model_id)

            # Prepare initialization parameters
            init_params = {
                "model": self.model_id,
                "region_name": self.region_name,
            }

            # Add AWS credentials if provided
            if self.aws_access_key_id:
                init_params["aws_access_key_id"] = self.aws_access_key_id
                logger.debug(
                    i18n.t('components.amazon.amazon_bedrock_converse.logs.access_key_added'))

            if self.aws_secret_access_key:
                init_params["aws_secret_access_key"] = self.aws_secret_access_key
                logger.debug(
                    i18n.t('components.amazon.amazon_bedrock_converse.logs.secret_key_added'))

            if self.aws_session_token:
                init_params["aws_session_token"] = self.aws_session_token
                logger.debug(
                    i18n.t('components.amazon.amazon_bedrock_converse.logs.session_token_added'))

            if self.credentials_profile_name:
                init_params["credentials_profile_name"] = self.credentials_profile_name
                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.profile_name_added',
                                    profile=self.credentials_profile_name))

            if self.endpoint_url:
                init_params["endpoint_url"] = self.endpoint_url
                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.endpoint_url_added',
                                    url=self.endpoint_url))

            # Add model parameters directly as supported by ChatBedrockConverse
            if hasattr(self, "temperature") and self.temperature is not None:
                init_params["temperature"] = self.temperature
                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.temperature_set',
                                    value=self.temperature))

            if hasattr(self, "max_tokens") and self.max_tokens is not None:
                init_params["max_tokens"] = self.max_tokens
                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.max_tokens_set',
                                    value=self.max_tokens))

            if hasattr(self, "top_p") and self.top_p is not None:
                init_params["top_p"] = self.top_p
                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.top_p_set',
                                    value=self.top_p))

            # Handle streaming - only disable if explicitly requested
            if hasattr(self, "disable_streaming") and self.disable_streaming:
                init_params["disable_streaming"] = True
                logger.info(
                    i18n.t('components.amazon.amazon_bedrock_converse.logs.streaming_disabled'))

            # Handle additional model request fields carefully
            additional_model_request_fields = {}

            # Only add top_k if user explicitly provided additional fields or if needed for specific models
            if hasattr(self, "additional_model_fields") and self.additional_model_fields:
                for field in self.additional_model_fields:
                    if isinstance(field, dict):
                        additional_model_request_fields.update(field)

                logger.debug(i18n.t('components.amazon.amazon_bedrock_converse.logs.additional_fields_added',
                                    fields=str(additional_model_request_fields)))

            # Only add if we have actual additional fields
            if additional_model_request_fields:
                init_params["additional_model_request_fields"] = additional_model_request_fields

            try:
                output = ChatBedrockConverse(**init_params)

                success_msg = i18n.t('components.amazon.amazon_bedrock_converse.success.model_initialized',
                                     model=self.model_id, region=self.region_name)
                logger.info(success_msg)
                self.status = success_msg

                return output

            except Exception as e:
                # Provide helpful error message with fallback suggestions
                error_details = str(e)

                if "validation error" in error_details.lower():
                    error_msg = i18n.t('components.amazon.amazon_bedrock_converse.errors.validation_error',
                                       error=error_details, model=self.model_id)
                elif "converse api" in error_details.lower():
                    error_msg = i18n.t('components.amazon.amazon_bedrock_converse.errors.converse_api_error',
                                       error=error_details, model=self.model_id)
                else:
                    error_msg = i18n.t('components.amazon.amazon_bedrock_converse.errors.initialization_failed',
                                       error=error_details)

                raise ValueError(error_msg) from e

        except (ImportError, ValueError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t('components.amazon.amazon_bedrock_converse.errors.model_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
