import os
import i18n
import json
from typing import Any

import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class ListHomeAssistantStates(LCToolComponent):
    display_name: str = "List Home Assistant States"
    description: str = i18n.t(
        'components.homeassistant.list_home_assistant_states.description')
    documentation: str = "https://developers.home-assistant.io/docs/api/rest/"
    icon = "HomeAssistant"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    # 1) Define fields to be received in LangFlow UI
    inputs = [
        SecretStrInput(
            name="ha_token",
            display_name=i18n.t(
                'components.homeassistant.list_home_assistant_states.ha_token.display_name'),
            info=i18n.t(
                'components.homeassistant.list_home_assistant_states.ha_token.info'),
            required=True,
        ),
        StrInput(
            name="base_url",
            display_name=i18n.t(
                'components.homeassistant.list_home_assistant_states.base_url.display_name'),
            info=i18n.t(
                'components.homeassistant.list_home_assistant_states.base_url.info'),
            required=True,
        ),
        StrInput(
            name="filter_domain",
            display_name=i18n.t(
                'components.homeassistant.list_home_assistant_states.filter_domain.display_name'),
            info=i18n.t(
                'components.homeassistant.list_home_assistant_states.filter_domain.info'),
            required=False,
        ),
    ]

    # 2) Pydantic schema containing only parameters exposed to the agent
    class ToolSchema(BaseModel):
        """Parameters to be passed by the agent: filter_domain only."""

        filter_domain: str = Field(
            "", description="Filter domain (e.g., 'light'). If empty, returns all.")

    def run_model(self) -> Data:
        """Execute the LangFlow component.

        Uses self.ha_token, self.base_url, self.filter_domain as entered in the UI.
        Triggered when 'Run' is clicked directly without an agent.

        Returns:
            Data: Home Assistant states data.
        """
        filter_domain = self.filter_domain or ""  # Use "" for fetching all states

        logger.info(i18n.t('components.homeassistant.list_home_assistant_states.logs.running_with_filter',
                           filter_domain=filter_domain or 'all'))

        result = self._list_states(
            ha_token=self.ha_token,
            base_url=self.base_url,
            filter_domain=filter_domain,
        )
        return self._make_data_response(result)

    def build_tool(self) -> Tool:
        """Build a tool object to be used by the agent.

        The agent can only pass 'filter_domain' as a parameter.
        'ha_token' and 'base_url' are not exposed (stored as self attributes).

        Returns:
            Tool: Structured tool for agent use.
        """
        logger.debug(i18n.t(
            'components.homeassistant.list_home_assistant_states.logs.building_tool'))

        return StructuredTool.from_function(
            name="list_homeassistant_states",
            description=(
                "Retrieve states from Home Assistant. "
                "You can provide filter_domain='light', 'switch', etc. to narrow results."
            ),
            func=self._list_states_for_tool,  # Wrapper function below
            args_schema=self.ToolSchema,  # Requires only filter_domain
        )

    def _list_states_for_tool(self, filter_domain: str = "") -> list[Any] | str:
        """Execute the tool when called by the agent.

        'ha_token' and 'base_url' are stored in self (not exposed).

        Args:
            filter_domain: Domain to filter by (e.g., 'light', 'switch').

        Returns:
            list or str: List of states or error message.
        """
        logger.info(i18n.t('components.homeassistant.list_home_assistant_states.logs.tool_invoked',
                           filter_domain=filter_domain or 'all'))

        return self._list_states(
            ha_token=self.ha_token,
            base_url=self.base_url,
            filter_domain=filter_domain,
        )

    def _list_states(
        self,
        ha_token: str,
        base_url: str,
        filter_domain: str = "",
    ) -> list[Any] | str:
        """Call the Home Assistant /api/states endpoint.

        Args:
            ha_token: Home Assistant access token.
            base_url: Home Assistant base URL.
            filter_domain: Domain to filter by (optional).

        Returns:
            list or str: List of states or error message.
        """
        try:
            logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.fetching_states',
                                base_url=base_url,
                                filter_domain=filter_domain or 'all'))

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            url = f"{base_url}/api/states"

            logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.requesting_url',
                                url=url))

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            all_states = response.json()
            total_count = len(all_states)

            logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.states_retrieved',
                                count=total_count))

            if filter_domain:
                logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.applying_filter',
                                    domain=filter_domain))

                filtered_states = [
                    st for st in all_states
                    if st.get("entity_id", "").startswith(f"{filter_domain}.")
                ]

                logger.info(i18n.t('components.homeassistant.list_home_assistant_states.logs.filtered_states',
                                   filtered_count=len(filtered_states),
                                   total_count=total_count,
                                   domain=filter_domain))

                return filtered_states

            logger.info(i18n.t('components.homeassistant.list_home_assistant_states.logs.returning_all_states',
                               count=total_count))
            return all_states

        except requests.exceptions.Timeout as e:
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.timeout',
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.ConnectionError as e:
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.connection_failed',
                               base_url=base_url,
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.HTTPError as e:
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.http_error',
                               status=response.status_code,
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.RequestException as e:
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.request_failed',
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except (ValueError, TypeError) as e:
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.processing_failed',
                               error=str(e))
            logger.error(error_msg)
            return error_msg

    def _make_data_response(self, result: list[Any] | str | dict) -> Data:
        """Format the response into a Data object.

        Args:
            result: States list, dict, or error message.

        Returns:
            Data: Formatted data response.
        """
        try:
            logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.formatting_response',
                                result_type=type(result).__name__))

            if isinstance(result, list):
                # Wrap list data into a dictionary and convert to text
                wrapped_result = {"result": result}
                logger.debug(i18n.t('components.homeassistant.list_home_assistant_states.logs.formatted_list',
                                    count=len(result)))
                return Data(data=wrapped_result, text=json.dumps(wrapped_result, indent=2, ensure_ascii=False))

            if isinstance(result, dict):
                # Return dictionary as-is
                logger.debug(i18n.t(
                    'components.homeassistant.list_home_assistant_states.logs.formatted_dict'))
                return Data(data=result, text=json.dumps(result, indent=2, ensure_ascii=False))

            if isinstance(result, str):
                # Return error messages or strings
                logger.debug(i18n.t(
                    'components.homeassistant.list_home_assistant_states.logs.formatted_string'))
                return Data(data={}, text=result)

            # Handle unexpected data types
            error_msg = i18n.t(
                'components.homeassistant.list_home_assistant_states.errors.unexpected_format')
            logger.warning(error_msg)
            return Data(data={}, text=error_msg)

        except (TypeError, ValueError) as e:
            # Handle specific exceptions during formatting
            error_msg = i18n.t('components.homeassistant.list_home_assistant_states.errors.formatting_failed',
                               error=str(e))
            logger.exception(error_msg)
            return Data(data={}, text=error_msg)
