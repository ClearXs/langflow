import i18n
import base64
import json
import re
from collections.abc import Iterator
from json.decoder import JSONDecodeError
from typing import Any

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.chat_sessions import ChatSession
from langchain_core.messages import HumanMessage
from langchain_google_community.gmail.loader import GMailLoader

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.io import SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.template.field.base import Output


class GmailLoaderComponent(Component):
    display_name = "Gmail Loader"
    description = i18n.t('components.google.gmail.description')
    icon = "Google"
    legacy: bool = True
    replacement = ["composio.ComposioGmailAPIComponent"]

    inputs = [
        SecretStrInput(
            name="json_string",
            display_name=i18n.t(
                'components.google.gmail.json_string.display_name'),
            info=i18n.t('components.google.gmail.json_string.info'),
            required=True,
            value="""{
                "account": "",
                "client_id": "",
                "client_secret": "",
                "expiry": "",
                "refresh_token": "",
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.readonly",
                ],
                "token": "",
                "token_uri": "https://oauth2.googleapis.com/token",
                "universe_domain": "googleapis.com"
            }""",
        ),
        MessageTextInput(
            name="label_ids",
            display_name=i18n.t(
                'components.google.gmail.label_ids.display_name'),
            info=i18n.t('components.google.gmail.label_ids.info'),
            required=True,
            value="INBOX,SENT,UNREAD,IMPORTANT",
        ),
        MessageTextInput(
            name="max_results",
            display_name=i18n.t(
                'components.google.gmail.max_results.display_name'),
            info=i18n.t('components.google.gmail.max_results.info'),
            required=True,
            value="10",
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.gmail.outputs.data.display_name'),
            name="data",
            method="load_emails"
        ),
    ]

    def load_emails(self) -> Data:
        """Load emails from Gmail using provided credentials.

        Returns:
            Data: Data object containing loaded emails.

        Raises:
            ValueError: If JSON is invalid, authentication fails, or loading fails.
        """
        class CustomGMailLoader(GMailLoader):
            def __init__(
                self, creds: Any, *, n: int = 100, label_ids: list[str] | None = None, raise_error: bool = False
            ) -> None:
                super().__init__(creds, n, raise_error)
                self.label_ids = label_ids if label_ids is not None else [
                    "SENT"]
                logger.debug(i18n.t('components.google.gmail.logs.loader_initialized',
                                    max_results=n,
                                    labels=",".join(self.label_ids)))

            def clean_message_content(self, message):
                """Clean message content by removing URLs, emails, and special characters."""
                logger.debug(i18n.t('components.google.gmail.logs.cleaning_message',
                                    length=len(message)))

                # Remove URLs
                message = re.sub(r"http\S+|www\S+|https\S+",
                                 "", message, flags=re.MULTILINE)

                # Remove email addresses
                message = re.sub(r"\S+@\S+", "", message)

                # Remove special characters and excessive whitespace
                message = re.sub(r"[^A-Za-z0-9\s]+", " ", message)
                message = re.sub(r"\s{2,}", " ", message)

                # Trim leading and trailing whitespace
                cleaned = message.strip()
                logger.debug(i18n.t('components.google.gmail.logs.message_cleaned',
                                    original_length=len(message),
                                    cleaned_length=len(cleaned)))
                return cleaned

            def _extract_email_content(self, msg: Any) -> HumanMessage:
                """Extract email content from message payload."""
                logger.debug(
                    i18n.t('components.google.gmail.logs.extracting_content'))

                from_email = None
                for values in msg["payload"]["headers"]:
                    name = values["name"]
                    if name == "From":
                        from_email = values["value"]

                if from_email is None:
                    error_msg = i18n.t(
                        'components.google.gmail.errors.from_email_not_found')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(i18n.t('components.google.gmail.logs.from_email_found',
                                    email=from_email))

                parts = msg["payload"]["parts"] if "parts" in msg["payload"] else [
                    msg["payload"]]

                for part in parts:
                    if part["mimeType"] == "text/plain":
                        data = part["body"]["data"]
                        data = base64.urlsafe_b64decode(data).decode("utf-8")
                        pattern = re.compile(r"\r\nOn .+(\r\n)*wrote:\r\n")
                        newest_response = re.split(pattern, data)[0]

                        logger.debug(
                            i18n.t('components.google.gmail.logs.content_extracted'))

                        return HumanMessage(
                            content=self.clean_message_content(
                                newest_response),
                            additional_kwargs={"sender": from_email},
                        )

                error_msg = i18n.t(
                    'components.google.gmail.errors.no_plain_text')
                logger.error(error_msg)
                raise ValueError(error_msg)

            def _get_message_data(self, service: Any, message: Any) -> ChatSession:
                """Get message data including thread context if available."""
                logger.debug(i18n.t('components.google.gmail.logs.getting_message_data',
                                    message_id=message["id"]))

                msg = service.users().messages().get(
                    userId="me", id=message["id"]).execute()
                message_content = self._extract_email_content(msg)

                in_reply_to = None
                email_data = msg["payload"]["headers"]
                for values in email_data:
                    name = values["name"]
                    if name == "In-Reply-To":
                        in_reply_to = values["value"]

                thread_id = msg["threadId"]

                if in_reply_to:
                    logger.debug(i18n.t('components.google.gmail.logs.processing_thread',
                                        thread_id=thread_id))

                    thread = service.users().threads().get(userId="me", id=thread_id).execute()
                    messages = thread["messages"]

                    response_email = None
                    for _message in messages:
                        email_data = _message["payload"]["headers"]
                        for values in email_data:
                            if values["name"] == "Message-ID":
                                message_id = values["value"]
                                if message_id == in_reply_to:
                                    response_email = _message

                    if response_email is None:
                        error_msg = i18n.t(
                            'components.google.gmail.errors.response_email_not_found')
                        logger.warning(error_msg)
                        raise ValueError(error_msg)

                    starter_content = self._extract_email_content(
                        response_email)
                    logger.debug(
                        i18n.t('components.google.gmail.logs.thread_context_added'))
                    return ChatSession(messages=[starter_content, message_content])

                logger.debug(
                    i18n.t('components.google.gmail.logs.single_message'))
                return ChatSession(messages=[message_content])

            def lazy_load(self) -> Iterator[ChatSession]:
                """Lazy load emails from Gmail."""
                logger.info(
                    i18n.t('components.google.gmail.logs.starting_lazy_load'))

                service = build("gmail", "v1", credentials=self.creds)
                results = (
                    service.users().messages().list(
                        userId="me", labelIds=self.label_ids, maxResults=self.n).execute()
                )
                messages = results.get("messages", [])

                if not messages:
                    warning_msg = i18n.t(
                        'components.google.gmail.logs.no_messages_found')
                    logger.warning(warning_msg)

                logger.info(i18n.t('components.google.gmail.logs.messages_found',
                                   count=len(messages)))

                for idx, message in enumerate(messages, 1):
                    try:
                        logger.debug(i18n.t('components.google.gmail.logs.processing_message',
                                            index=idx,
                                            total=len(messages),
                                            message_id=message['id']))
                        yield self._get_message_data(service, message)
                    except Exception as e:
                        if self.raise_error:
                            raise
                        else:
                            logger.exception(i18n.t('components.google.gmail.logs.message_processing_error',
                                                    message_id=message['id'],
                                                    error=str(e)))

        logger.info(i18n.t('components.google.gmail.logs.loading_emails'))

        json_string = self.json_string
        label_ids = self.label_ids.split(",") if self.label_ids else ["INBOX"]
        max_results = int(self.max_results) if self.max_results else 100

        logger.debug(i18n.t('components.google.gmail.logs.parameters_parsed',
                            labels=",".join(label_ids),
                            max_results=max_results))

        # Load the token information from the JSON string
        try:
            logger.debug(i18n.t('components.google.gmail.logs.parsing_json'))
            token_info = json.loads(json_string)
            logger.debug(i18n.t('components.google.gmail.logs.json_parsed'))
        except JSONDecodeError as e:
            error_msg = i18n.t('components.google.gmail.errors.invalid_json')
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        try:
            logger.debug(
                i18n.t('components.google.gmail.logs.creating_credentials'))
            creds = Credentials.from_authorized_user_info(token_info)
            logger.debug(
                i18n.t('components.google.gmail.logs.credentials_created'))
        except Exception as e:
            error_msg = i18n.t('components.google.gmail.errors.credentials_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Initialize the custom loader with the provided credentials
        logger.info(i18n.t('components.google.gmail.logs.initializing_loader'))
        loader = CustomGMailLoader(
            creds=creds, n=max_results, label_ids=label_ids)

        try:
            logger.info(
                i18n.t('components.google.gmail.logs.loading_documents'))
            docs = loader.load()
            logger.info(i18n.t('components.google.gmail.logs.documents_loaded',
                               count=len(docs)))
        except RefreshError as e:
            error_msg = i18n.t(
                'components.google.gmail.errors.auth_refresh_failed')
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t('components.google.gmail.errors.loading_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Return the loaded documents
        self.status = docs
        return Data(data={"text": docs})
