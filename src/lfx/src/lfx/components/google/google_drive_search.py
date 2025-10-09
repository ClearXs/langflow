import i18n
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput
from lfx.io import SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.template.field.base import Output


class GoogleDriveSearchComponent(Component):
    display_name = "Google Drive Search"
    description = i18n.t('components.google.google_drive_search.description')
    icon = "Google"
    legacy: bool = True
    replacement = ["composio.ComposioGoogleDriveAPIComponent"]

    inputs = [
        SecretStrInput(
            name="token_string",
            display_name=i18n.t(
                'components.google.google_drive_search.token_string.display_name'),
            info=i18n.t(
                'components.google.google_drive_search.token_string.info'),
            required=True,
        ),
        DropdownInput(
            name="query_item",
            display_name=i18n.t(
                'components.google.google_drive_search.query_item.display_name'),
            options=[
                "name",
                "fullText",
                "mimeType",
                "modifiedTime",
                "viewedByMeTime",
                "trashed",
                "starred",
                "parents",
                "owners",
                "writers",
                "readers",
                "sharedWithMe",
                "createdTime",
                "properties",
                "appProperties",
                "visibility",
                "shortcutDetails.targetId",
            ],
            info=i18n.t(
                'components.google.google_drive_search.query_item.info'),
            required=True,
        ),
        DropdownInput(
            name="valid_operator",
            display_name=i18n.t(
                'components.google.google_drive_search.valid_operator.display_name'),
            options=["contains", "=", "!=", "<=", "<", ">", ">=", "in", "has"],
            info=i18n.t(
                'components.google.google_drive_search.valid_operator.info'),
            required=True,
        ),
        MessageTextInput(
            name="search_term",
            display_name=i18n.t(
                'components.google.google_drive_search.search_term.display_name'),
            info=i18n.t(
                'components.google.google_drive_search.search_term.info'),
            required=True,
        ),
        MessageTextInput(
            name="query_string",
            display_name=i18n.t(
                'components.google.google_drive_search.query_string.display_name'),
            info=i18n.t(
                'components.google.google_drive_search.query_string.info'),
            value="",  # This will be updated with the generated query string
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_drive_search.outputs.doc_urls.display_name'),
            name="doc_urls",
            method="search_doc_urls"
        ),
        Output(
            display_name=i18n.t(
                'components.google.google_drive_search.outputs.doc_ids.display_name'),
            name="doc_ids",
            method="search_doc_ids"
        ),
        Output(
            display_name=i18n.t(
                'components.google.google_drive_search.outputs.doc_titles.display_name'),
            name="doc_titles",
            method="search_doc_titles"
        ),
        Output(
            display_name=i18n.t(
                'components.google.google_drive_search.outputs.data.display_name'),
            name="Data",
            method="search_data"
        ),
    ]

    def generate_query_string(self) -> str:
        """Generate Google Drive query string from search parameters.

        Returns:
            str: The generated query string.
        """
        query_item = self.query_item
        valid_operator = self.valid_operator
        search_term = self.search_term

        # Construct the query string
        query = f"{query_item} {valid_operator} '{search_term}'"

        # Update the editable query string input with the generated query
        self.query_string = query

        logger.debug(i18n.t('components.google.google_drive_search.logs.query_generated',
                            query=query))

        return query

    def on_inputs_changed(self) -> None:
        """Automatically regenerate the query string when inputs change."""
        logger.debug(
            i18n.t('components.google.google_drive_search.logs.inputs_changed'))
        self.generate_query_string()

    def generate_file_url(self, file_id: str, mime_type: str) -> str:
        """Generate the appropriate Google Drive URL for a file based on its MIME type.

        Args:
            file_id: The Google Drive file ID.
            mime_type: The MIME type of the file.

        Returns:
            str: The appropriate URL for accessing the file.
        """
        url_map = {
            "application/vnd.google-apps.document": f"https://docs.google.com/document/d/{file_id}/edit",
            "application/vnd.google-apps.spreadsheet": f"https://docs.google.com/spreadsheets/d/{file_id}/edit",
            "application/vnd.google-apps.presentation": f"https://docs.google.com/presentation/d/{file_id}/edit",
            "application/vnd.google-apps.drawing": f"https://docs.google.com/drawings/d/{file_id}/edit",
            "application/pdf": f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk",
        }

        url = url_map.get(
            mime_type, f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk")

        logger.debug(i18n.t('components.google.google_drive_search.logs.url_generated',
                            file_id=file_id,
                            mime_type=mime_type))

        return url

    def search_files(self) -> dict:
        """Search Google Drive files using the configured query.

        Returns:
            dict: Dictionary containing doc_urls, doc_ids, doc_titles_urls, and doc_titles.

        Raises:
            ValueError: If token parsing or API call fails.
        """
        try:
            logger.info(
                i18n.t('components.google.google_drive_search.logs.starting_search'))

            # Load the token information from the JSON string
            logger.debug(
                i18n.t('components.google.google_drive_search.logs.parsing_token'))
            token_info = json.loads(self.token_string)
            creds = Credentials.from_authorized_user_info(token_info)
            logger.debug(
                i18n.t('components.google.google_drive_search.logs.credentials_created'))

            # Use the query string from the input (which might have been edited by the user)
            query = self.query_string or self.generate_query_string()
            logger.info(i18n.t('components.google.google_drive_search.logs.using_query',
                               query=query))

            # Initialize the Google Drive API service
            logger.debug(
                i18n.t('components.google.google_drive_search.logs.building_service'))
            service = build("drive", "v3", credentials=creds)

            # Perform the search
            logger.debug(
                i18n.t('components.google.google_drive_search.logs.executing_search'))
            results = service.files().list(
                q=query,
                pageSize=5,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()

            items = results.get("files", [])
            logger.info(i18n.t('components.google.google_drive_search.logs.search_completed',
                               count=len(items)))

            doc_urls = []
            doc_ids = []
            doc_titles_urls = []
            doc_titles = []

            if items:
                logger.debug(
                    i18n.t('components.google.google_drive_search.logs.processing_results'))

                for idx, item in enumerate(items, 1):
                    # Directly use the file ID, title, and MIME type to generate the URL
                    file_id = item["id"]
                    file_title = item["name"]
                    mime_type = item["mimeType"]
                    file_url = self.generate_file_url(file_id, mime_type)

                    # Store the URL, ID, and title+URL in their respective lists
                    doc_urls.append(file_url)
                    doc_ids.append(file_id)
                    doc_titles.append(file_title)
                    doc_titles_urls.append(
                        {"title": file_title, "url": file_url})

                    logger.debug(i18n.t('components.google.google_drive_search.logs.file_processed',
                                        index=idx,
                                        title=file_title,
                                        id=file_id))
            else:
                logger.warning(
                    i18n.t('components.google.google_drive_search.logs.no_files_found'))

            result = {
                "doc_urls": doc_urls,
                "doc_ids": doc_ids,
                "doc_titles_urls": doc_titles_urls,
                "doc_titles": doc_titles
            }

            self.status = result
            return result

        except json.JSONDecodeError as e:
            error_msg = i18n.t(
                'components.google.google_drive_search.errors.invalid_token_json')
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t('components.google.google_drive_search.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def search_doc_ids(self) -> list[str]:
        """Search and return document IDs.

        Returns:
            list[str]: List of document IDs.
        """
        logger.info(
            i18n.t('components.google.google_drive_search.logs.returning_doc_ids'))
        return self.search_files()["doc_ids"]

    def search_doc_urls(self) -> list[str]:
        """Search and return document URLs.

        Returns:
            list[str]: List of document URLs.
        """
        logger.info(
            i18n.t('components.google.google_drive_search.logs.returning_doc_urls'))
        return self.search_files()["doc_urls"]

    def search_doc_titles(self) -> list[str]:
        """Search and return document titles.

        Returns:
            list[str]: List of document titles.
        """
        logger.info(
            i18n.t('components.google.google_drive_search.logs.returning_doc_titles'))
        return self.search_files()["doc_titles"]

    def search_data(self) -> Data:
        """Search and return structured data.

        Returns:
            Data: Data object containing titles and URLs.
        """
        logger.info(
            i18n.t('components.google.google_drive_search.logs.returning_data'))
        return Data(data={"text": self.search_files()["doc_titles_urls"]})
