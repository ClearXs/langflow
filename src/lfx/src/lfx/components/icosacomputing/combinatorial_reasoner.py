import os
import i18n
import requests
from requests.auth import HTTPBasicAuth

from lfx.base.models.openai_constants import OPENAI_CHAT_MODEL_NAMES
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, SecretStrInput, StrInput
from lfx.io import MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.message import Message


class CombinatorialReasonerComponent(Component):
    display_name = "Combinatorial Reasoner"
    description = i18n.t(
        'components.icosacomputing.combinatorial_reasoner.description')
    icon = "Icosa"
    name = "Combinatorial Reasoner"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="prompt",
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.prompt.display_name'),
            required=True
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.openai_api_key.display_name'),
            info=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.openai_api_key.info'),
            advanced=False,
            value="OPENAI_API_KEY",
            required=True,
        ),
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.username.display_name'),
            info=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.username.info'),
            advanced=False,
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.password.display_name'),
            info=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.password.info'),
            advanced=False,
            required=True,
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.model_name.display_name'),
            advanced=False,
            options=OPENAI_CHAT_MODEL_NAMES,
            value=OPENAI_CHAT_MODEL_NAMES[0],
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.outputs.optimized_prompt.display_name'),
            name="optimized_prompt",
            method="build_prompt",
        ),
        Output(
            display_name=i18n.t(
                'components.icosacomputing.combinatorial_reasoner.outputs.reasons.display_name'),
            name="reasons",
            method="build_reasons"
        ),
    ]

    def build_prompt(self) -> Message:
        """Build optimized prompt using combinatorial reasoning.

        Returns:
            Message: The optimized prompt.

        Raises:
            requests.HTTPError: If the API request fails.
            requests.Timeout: If the request times out.
            requests.RequestException: For other request-related errors.
        """
        logger.info(i18n.t('components.icosacomputing.combinatorial_reasoner.logs.building_prompt',
                           prompt_length=len(self.prompt),
                           model=self.model_name))

        params = {
            "prompt": self.prompt,
            "apiKey": self.openai_api_key,
            "model": self.model_name,
        }

        logger.debug(i18n.t('components.icosacomputing.combinatorial_reasoner.logs.authenticating',
                            username=self.username))

        creds = HTTPBasicAuth(self.username, password=self.password)

        try:
            logger.debug(
                i18n.t('components.icosacomputing.combinatorial_reasoner.logs.sending_request'))

            response = requests.post(
                "https://cr-api.icosacomputing.com/cr/langflow",
                json=params,
                auth=creds,
                timeout=100,
            )

            logger.debug(i18n.t('components.icosacomputing.combinatorial_reasoner.logs.response_received',
                                status=response.status_code))

            response.raise_for_status()

            response_data = response.json()
            prompt = response_data["prompt"]
            self.reasons = response_data["finalReasons"]

            logger.info(i18n.t('components.icosacomputing.combinatorial_reasoner.logs.optimization_complete',
                               reasons_count=len(self.reasons),
                               optimized_length=len(prompt)))

            return prompt

        except requests.exceptions.Timeout:
            error_msg = i18n.t(
                'components.icosacomputing.combinatorial_reasoner.errors.timeout')
            logger.error(error_msg)
            raise

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'

            if status_code == 401:
                error_msg = i18n.t(
                    'components.icosacomputing.combinatorial_reasoner.errors.authentication_failed')
            elif status_code == 403:
                error_msg = i18n.t(
                    'components.icosacomputing.combinatorial_reasoner.errors.access_denied')
            elif status_code == 429:
                error_msg = i18n.t(
                    'components.icosacomputing.combinatorial_reasoner.errors.rate_limit')
            elif status_code >= 500:
                error_msg = i18n.t('components.icosacomputing.combinatorial_reasoner.errors.server_error',
                                   status=status_code)
            else:
                error_msg = i18n.t('components.icosacomputing.combinatorial_reasoner.errors.http_error',
                                   status=status_code,
                                   error=str(e))

            logger.error(error_msg)
            raise

        except requests.exceptions.ConnectionError:
            error_msg = i18n.t(
                'components.icosacomputing.combinatorial_reasoner.errors.connection_failed')
            logger.error(error_msg)
            raise

        except requests.exceptions.RequestException as e:
            error_msg = i18n.t('components.icosacomputing.combinatorial_reasoner.errors.request_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise

        except (KeyError, ValueError) as e:
            error_msg = i18n.t('components.icosacomputing.combinatorial_reasoner.errors.invalid_response',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def build_reasons(self) -> Data:
        """Extract selected reasons from optimization.

        Returns:
            Data: List of selected reasons.
        """
        logger.debug(i18n.t(
            'components.icosacomputing.combinatorial_reasoner.logs.extracting_reasons'))

        if not hasattr(self, 'reasons') or not self.reasons:
            logger.warning(
                i18n.t('components.icosacomputing.combinatorial_reasoner.logs.no_reasons'))
            return Data(value=[])

        # List of selected reasons
        final_reasons = [reason[0] for reason in self.reasons]

        logger.info(i18n.t('components.icosacomputing.combinatorial_reasoner.logs.reasons_extracted',
                           count=len(final_reasons)))

        return Data(value=final_reasons)
