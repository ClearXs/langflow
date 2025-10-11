import os
import i18n
from langchain_community.embeddings.cloudflare_workersai import CloudflareWorkersAIEmbeddings

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import Embeddings
from lfx.io import BoolInput, DictInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger


class CloudflareWorkersAIEmbeddingsComponent(LCModelComponent):
    display_name: str = i18n.t('components.cloudflare.cloudflare.display_name')
    description: str = i18n.t('components.cloudflare.cloudflare.description')
    documentation: str = "https://python.langchain.com/docs/integrations/text_embedding/cloudflare_workersai/"
    icon = "Cloudflare"
    name = "CloudflareWorkersAIEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="account_id",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.account_id.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.account_id.info'),
            required=True,
        ),
        SecretStrInput(
            name="api_token",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.api_token.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.api_token.info'),
            required=True,
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.model_name.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.model_name.info'),
            required=True,
            value="@cf/baai/bge-base-en-v1.5",
        ),
        BoolInput(
            name="strip_new_lines",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.strip_new_lines.display_name'),
            info=i18n.t(
                'components.cloudflare.cloudflare.strip_new_lines.info'),
            advanced=True,
            value=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.batch_size.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.batch_size.info'),
            advanced=True,
            value=50,
        ),
        MessageTextInput(
            name="api_base_url",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.api_base_url.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.api_base_url.info'),
            advanced=True,
            value="https://api.cloudflare.com/client/v4/accounts",
        ),
        DictInput(
            name="headers",
            display_name=i18n.t(
                'components.cloudflare.cloudflare.headers.display_name'),
            info=i18n.t('components.cloudflare.cloudflare.headers.info'),
            is_list=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cloudflare.cloudflare.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        try:
            self.status = i18n.t(
                'components.cloudflare.cloudflare.status.initializing')
            logger.info(i18n.t('components.cloudflare.cloudflare.logs.initializing',
                               model=self.model_name,
                               account_id=self.account_id))

            embeddings = CloudflareWorkersAIEmbeddings(
                account_id=self.account_id,
                api_base_url=self.api_base_url,
                api_token=self.api_token,
                batch_size=self.batch_size,
                headers=self.headers,
                model_name=self.model_name,
                strip_new_lines=self.strip_new_lines,
            )

            success_msg = i18n.t('components.cloudflare.cloudflare.success.embeddings_created',
                                 model=self.model_name)
            self.status = success_msg
            logger.info(success_msg)

            return embeddings

        except Exception as e:
            error_msg = i18n.t('components.cloudflare.cloudflare.errors.connection_failed',
                               error=str(e))
            self.status = error_msg
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
