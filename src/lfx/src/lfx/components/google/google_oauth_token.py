import os
import i18n
import json
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from lfx.custom.custom_component.component import Component
from lfx.io import FileInput, MultilineInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class GoogleOAuthToken(Component):
    display_name = "Google OAuth Token"
    description = i18n.t('components.google.google_oauth_token.description')
    documentation: str = "https://developers.google.com/identity/protocols/oauth2/web-server?hl=pt-br#python_1"
    icon = "Google"
    name = "GoogleOAuthToken"
    legacy: bool = True

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MultilineInput(
            name="scopes",
            display_name=i18n.t(
                'components.google.google_oauth_token.scopes.display_name'),
            info=i18n.t('components.google.google_oauth_token.scopes.info'),
            required=True,
        ),
        FileInput(
            name="oauth_credentials",
            display_name=i18n.t(
                'components.google.google_oauth_token.oauth_credentials.display_name'),
            info=i18n.t(
                'components.google.google_oauth_token.oauth_credentials.info'),
            file_types=["json"],
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_oauth_token.outputs.output.display_name'),
            name="output",
            method="build_output"
        ),
    ]

    def validate_scopes(self, scopes: str) -> None:
        """Validate the format of OAuth scopes.

        Args:
            scopes: Comma-separated list of OAuth scopes.

        Raises:
            ValueError: If scope format is invalid.
        """
        logger.debug(
            i18n.t('components.google.google_oauth_token.logs.validating_scopes'))

        pattern = (
            r"^(https://www\.googleapis\.com/auth/[\w\.\-]+"
            r"|mail\.google\.com/"
            r"|www\.google\.com/calendar/feeds"
            r"|www\.google\.com/m8/feeds)"
            r"(,\s*https://www\.googleapis\.com/auth/[\w\.\-]+"
            r"|mail\.google\.com/"
            r"|www\.google\.com/calendar/feeds"
            r"|www\.google\.com/m8/feeds)*$"
        )

        if not re.match(pattern, scopes):
            error_message = i18n.t(
                'components.google.google_oauth_token.errors.invalid_scope_format')
            logger.error(error_message)
            raise ValueError(error_message)

        logger.debug(
            i18n.t('components.google.google_oauth_token.logs.scopes_validated'))

    def build_output(self) -> Data:
        """Build OAuth token and return credentials data.

        Returns:
            Data: Data object containing OAuth credentials.

        Raises:
            ValueError: If scopes are invalid or credentials file is missing.
        """
        logger.info(
            i18n.t('components.google.google_oauth_token.logs.building_oauth_token'))

        # Validate scopes
        self.validate_scopes(self.scopes)

        # Parse scopes
        user_scopes = [scope.strip() for scope in self.scopes.split(",")]
        logger.debug(i18n.t('components.google.google_oauth_token.logs.scopes_parsed',
                            count=len(user_scopes)))

        if self.scopes:
            scopes = user_scopes
        else:
            error_message = i18n.t(
                'components.google.google_oauth_token.errors.incorrect_scope')
            logger.error(error_message)
            raise ValueError(error_message)

        creds = None
        token_path = Path("token.json")

        # Check for existing token
        if token_path.exists():
            logger.debug(
                i18n.t('components.google.google_oauth_token.logs.token_file_found'))
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_path), scopes)
                logger.debug(i18n.t(
                    'components.google.google_oauth_token.logs.credentials_loaded_from_file'))
            except Exception as e:
                logger.warning(i18n.t('components.google.google_oauth_token.logs.token_load_failed',
                                      error=str(e)))

        # Handle credential validation and refresh
        if not creds or not creds.valid:
            logger.debug(
                i18n.t('components.google.google_oauth_token.logs.credentials_invalid'))

            if creds and creds.expired and creds.refresh_token:
                logger.info(
                    i18n.t('components.google.google_oauth_token.logs.refreshing_credentials'))
                try:
                    creds.refresh(Request())
                    logger.info(
                        i18n.t('components.google.google_oauth_token.logs.credentials_refreshed'))
                except Exception as e:
                    error_message = i18n.t('components.google.google_oauth_token.errors.refresh_failed',
                                           error=str(e))
                    logger.exception(error_message)
                    raise ValueError(error_message) from e
            else:
                logger.info(
                    i18n.t('components.google.google_oauth_token.logs.initiating_oauth_flow'))

                if self.oauth_credentials:
                    client_secret_file = self.oauth_credentials
                    logger.debug(
                        i18n.t('components.google.google_oauth_token.logs.credentials_file_provided'))
                else:
                    error_message = i18n.t(
                        'components.google.google_oauth_token.errors.no_credentials_file')
                    logger.error(error_message)
                    raise ValueError(error_message)

                try:
                    logger.debug(
                        i18n.t('components.google.google_oauth_token.logs.creating_oauth_flow'))
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secret_file, scopes)

                    logger.info(
                        i18n.t('components.google.google_oauth_token.logs.starting_local_server'))
                    creds = flow.run_local_server(port=0)

                    logger.info(
                        i18n.t('components.google.google_oauth_token.logs.oauth_completed'))
                except Exception as e:
                    error_message = i18n.t('components.google.google_oauth_token.errors.oauth_flow_failed',
                                           error=str(e))
                    logger.exception(error_message)
                    raise ValueError(error_message) from e

                # Save token
                try:
                    logger.debug(
                        i18n.t('components.google.google_oauth_token.logs.saving_token'))
                    token_path.write_text(creds.to_json(), encoding="utf-8")
                    logger.info(
                        i18n.t('components.google.google_oauth_token.logs.token_saved'))
                except Exception as e:
                    logger.warning(i18n.t('components.google.google_oauth_token.logs.token_save_failed',
                                          error=str(e)))

        # Convert credentials to JSON
        try:
            logger.debug(
                i18n.t('components.google.google_oauth_token.logs.converting_to_json'))
            creds_json = json.loads(creds.to_json())
            logger.info(
                i18n.t('components.google.google_oauth_token.logs.token_generated'))
        except Exception as e:
            error_message = i18n.t('components.google.google_oauth_token.errors.json_conversion_failed',
                                   error=str(e))
            logger.exception(error_message)
            raise ValueError(error_message) from e

        self.status = i18n.t(
            'components.google.google_oauth_token.logs.status_ready')
        return Data(data=creds_json)
