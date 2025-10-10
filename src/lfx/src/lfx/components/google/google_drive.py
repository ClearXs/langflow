import os
import i18n
import json
from json.decoder import JSONDecodeError

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from langchain_google_community import GoogleDriveLoader

from lfx.custom.custom_component.component import Component
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import MessageTextInput
from lfx.io import SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.template.field.base import Output


class GoogleDriveComponent(Component):
    display_name = "Google Drive Loader"
    description = i18n.t('components.google.google_drive.description')
    icon = "Google"
    legacy: bool = True

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="json_string",
            display_name=i18n.t(
                'components.google.google_drive.json_string.display_name'),
            info=i18n.t('components.google.google_drive.json_string.info'),
            required=True,
        ),
        MessageTextInput(
            name="document_id",
            display_name=i18n.t(
                'components.google.google_drive.document_id.display_name'),
            info=i18n.t('components.google.google_drive.document_id.info'),
            required=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_drive.outputs.docs.display_name'),
            name="docs",
            method="load_documents"
        ),
    ]

    def load_documents(self) -> Data:
        """Load a single document from Google Drive.

        Returns:
            Data: Data object containing the loaded document.

        Raises:
            ValueError: If JSON is invalid, document ID is invalid, authentication fails, or loading fails.
        """
        class CustomGoogleDriveLoader(GoogleDriveLoader):
            creds: Credentials | None = None
            """Credentials object to be passed directly."""

            def _load_credentials(self):
                """Load credentials from the provided creds attribute or fallback to the original method."""
                if self.creds:
                    logger.debug(
                        i18n.t('components.google.google_drive.logs.credentials_loaded'))
                    return self.creds
                error_msg = i18n.t(
                    'components.google.google_drive.errors.no_credentials')
                logger.error(error_msg)
                raise ValueError(error_msg)

            class Config:
                arbitrary_types_allowed = True

        logger.info(
            i18n.t('components.google.google_drive.logs.loading_document'))

        json_string = self.json_string
        document_ids = [self.document_id]

        # Validate single document ID
        if len(document_ids) != 1:
            error_msg = i18n.t(
                'components.google.google_drive.errors.single_document_expected')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(i18n.t('components.google.google_drive.logs.document_id_validated',
                            document_id=self.document_id))

        # Load the token information from the JSON string
        try:
            logger.debug(
                i18n.t('components.google.google_drive.logs.parsing_json'))
            token_info = json.loads(json_string)
            logger.debug(
                i18n.t('components.google.google_drive.logs.json_parsed'))
        except JSONDecodeError as e:
            error_msg = i18n.t(
                'components.google.google_drive.errors.invalid_json')
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        # Create credentials
        try:
            logger.debug(
                i18n.t('components.google.google_drive.logs.creating_credentials'))
            creds = Credentials.from_authorized_user_info(token_info)
            logger.debug(
                i18n.t('components.google.google_drive.logs.credentials_created'))
        except Exception as e:
            error_msg = i18n.t('components.google.google_drive.errors.credentials_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Initialize the custom loader with the provided credentials and document IDs
        logger.debug(
            i18n.t('components.google.google_drive.logs.initializing_loader'))
        loader = CustomGoogleDriveLoader(
            creds=creds,
            document_ids=document_ids
        )

        # Load the documents
        try:
            logger.info(i18n.t('components.google.google_drive.logs.loading_from_drive',
                               document_id=self.document_id))
            docs = loader.load()
            logger.info(i18n.t('components.google.google_drive.logs.documents_loaded',
                               count=len(docs)))
        except RefreshError as e:
            error_msg = i18n.t(
                'components.google.google_drive.errors.auth_refresh_failed')
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t('components.google.google_drive.errors.loading_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Validate that exactly one document was loaded
        if len(docs) != 1:
            error_msg = i18n.t('components.google.google_drive.errors.single_document_load_expected',
                               count=len(docs))
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            i18n.t('components.google.google_drive.logs.converting_to_data'))
        data = docs_to_data(docs)

        logger.info(
            i18n.t('components.google.google_drive.logs.load_successful'))

        # Return the loaded documents
        self.status = data
        return Data(data={"text": data})
