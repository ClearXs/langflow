import os
import i18n
from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders.confluence import ContentFormat

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DropdownInput, IntInput, Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class ConfluenceComponent(Component):
    display_name = i18n.t('components.confluence.confluence.display_name')
    description = i18n.t('components.confluence.confluence.description')
    documentation = "https://python.langchain.com/v0.2/docs/integrations/document_loaders/confluence/"
    trace_type = "tool"
    icon = "Confluence"
    name = "Confluence"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"    

    inputs = [
        StrInput(
            name="url",
            display_name=i18n.t(
                'components.confluence.confluence.url.display_name'),
            required=True,
            info=i18n.t('components.confluence.confluence.url.info'),
        ),
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.confluence.confluence.username.display_name'),
            required=True,
            info=i18n.t('components.confluence.confluence.username.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.confluence.confluence.api_key.display_name'),
            required=True,
            info=i18n.t('components.confluence.confluence.api_key.info'),
        ),
        StrInput(
            name="space_key",
            display_name=i18n.t(
                'components.confluence.confluence.space_key.display_name'),
            required=True,
            info=i18n.t('components.confluence.confluence.space_key.info'),
        ),
        BoolInput(
            name="cloud",
            display_name=i18n.t(
                'components.confluence.confluence.cloud.display_name'),
            required=True,
            value=True,
            advanced=True,
            info=i18n.t('components.confluence.confluence.cloud.info'),
        ),
        DropdownInput(
            name="content_format",
            display_name=i18n.t(
                'components.confluence.confluence.content_format.display_name'),
            options=[
                ContentFormat.EDITOR.value,
                ContentFormat.EXPORT_VIEW.value,
                ContentFormat.ANONYMOUS_EXPORT_VIEW.value,
                ContentFormat.STORAGE.value,
                ContentFormat.VIEW.value,
            ],
            value=ContentFormat.STORAGE.value,
            required=True,
            advanced=True,
            info=i18n.t(
                'components.confluence.confluence.content_format.info'),
        ),
        IntInput(
            name="max_pages",
            display_name=i18n.t(
                'components.confluence.confluence.max_pages.display_name'),
            required=False,
            value=1000,
            advanced=True,
            info=i18n.t('components.confluence.confluence.max_pages.info'),
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t(
                'components.confluence.confluence.outputs.data.display_name'),
            method="load_documents"
        ),
    ]

    def build_confluence(self) -> ConfluenceLoader:
        """Build and configure the Confluence loader.

        Returns:
            ConfluenceLoader: Configured Confluence document loader.
        """
        try:
            logger.debug(
                i18n.t('components.confluence.confluence.logs.building_loader'))

            content_format = ContentFormat(self.content_format)

            loader = ConfluenceLoader(
                url=self.url,
                username=self.username,
                api_key=self.api_key,
                cloud=self.cloud,
                space_key=self.space_key,
                content_format=content_format,
                max_pages=self.max_pages,
            )

            logger.info(i18n.t('components.confluence.confluence.logs.loader_built',
                               space_key=self.space_key,
                               max_pages=self.max_pages))

            return loader

        except Exception as e:
            error_msg = i18n.t('components.confluence.confluence.errors.loader_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def load_documents(self) -> list[Data]:
        """Load documents from Confluence space.

        Returns:
            list[Data]: List of Data objects containing the loaded documents.
        """
        try:
            logger.info(i18n.t('components.confluence.confluence.logs.loading_documents',
                               space_key=self.space_key))

            self.status = i18n.t('components.confluence.confluence.status.connecting',
                                 space_key=self.space_key)

            confluence = self.build_confluence()

            self.status = i18n.t(
                'components.confluence.confluence.status.loading')
            logger.debug(
                i18n.t('components.confluence.confluence.logs.fetching_pages'))

            documents = confluence.load()

            logger.info(i18n.t('components.confluence.confluence.logs.pages_loaded',
                               count=len(documents)))

            self.status = i18n.t('components.confluence.confluence.status.converting',
                                 count=len(documents))

            # Convert documents to Data objects
            data = [Data.from_document(doc) for doc in documents]

            success_msg = i18n.t('components.confluence.confluence.status.completed',
                                 count=len(data),
                                 space_key=self.space_key)
            self.status = success_msg
            logger.info(success_msg)

            return data

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.confluence.confluence.errors.load_failed',
                               space_key=self.space_key,
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
