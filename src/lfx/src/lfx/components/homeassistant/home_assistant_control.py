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


class HomeAssistantControl(LCToolComponent):
    """This tool is used to control Home Assistant devices.

    A very simple tool to control Home Assistant devices.
    - The agent only needs to provide action (turn_on, turn_off, toggle) + entity_id (e.g., switch.xxx, light.xxx).
    - The domain (e.g., 'switch', 'light') is automatically extracted from entity_id.
    """

    display_name: str = "Home Assistant Control"
    description: str = i18n.t(
        'components.homeassistant.home_assistant_control.description')
    documentation: str = "https://developers.home-assistant.io/docs/api/rest/"
    icon: str = "HomeAssistant"

    # --- Input fields for LangFlow UI (token, URL) ---
    inputs = [
        SecretStrInput(
            name="ha_token",
            display_name=i18n.t(
                'components.homeassistant.home_assistant_control.ha_token.display_name'),
            info=i18n.t(
                'components.homeassistant.home_assistant_control.ha_token.info'),
            required=True,
        ),
        StrInput(
            name="base_url",
            display_name=i18n.t(
                'components.homeassistant.home_assistant_control.base_url.display_name'),
            info=i18n.t(
                'components.homeassistant.home_assistant_control.base_url.info'),
            required=True,
        ),
        StrInput(
            name="default_action",
            display_name=i18n.t(
                'components.homeassistant.home_assistant_control.default_action.display_name'),
            info=i18n.t(
                'components.homeassistant.home_assistant_control.default_action.info'),
            required=False,
        ),
        StrInput(
            name="default_entity_id",
            display_name=i18n.t(
                'components.homeassistant.home_assistant_control.default_entity_id.display_name'),
            info=i18n.t(
                'components.homeassistant.home_assistant_control.default_entity_id.info'),
            required=False,
        ),
    ]

    # --- Parameters exposed to the agent (Pydantic schema) ---
    class ToolSchema(BaseModel):
        """Parameters to be passed by the agent: action, entity_id only."""

        action: str = Field(
            ...,
            description="Home Assistant service name. (One of turn_on, turn_off, toggle)"
        )
        entity_id: str = Field(
            ...,
            description=(
                "Entity ID to control (e.g., switch.xxx, light.xxx, cover.xxx, etc.). "
                "Do not infer; use the list_homeassistant_states tool to retrieve it."
            ),
        )

    def run_model(self) -> Data:
        """Used when the 'Run' button is clicked in LangFlow.

        - Uses default_action and default_entity_id entered in the UI.

        Returns:
            Data: Control result data.
        """
        action = self.default_action or "turn_off"
        entity_id = self.default_entity_id or "switch.unknown_switch_3"

        logger.info(i18n.t('components.homeassistant.home_assistant_control.logs.running_with_defaults',
                           action=action,
                           entity_id=entity_id))

        result = self._control_device(
            ha_token=self.ha_token,
            base_url=self.base_url,
            action=action,
            entity_id=entity_id,
        )
        return self._make_data_response(result)

    def build_tool(self) -> Tool:
        """Returns a tool to be used by the agent (LLM).

        - The agent can only pass action and entity_id as arguments.

        Returns:
            Tool: Structured tool for agent use.
        """
        logger.debug(
            i18n.t('components.homeassistant.home_assistant_control.logs.building_tool'))

        return StructuredTool.from_function(
            name="home_assistant_control",
            description=(
                "A tool to control Home Assistant devices easily. "
                "Parameters: action ('turn_on'/'turn_off'/'toggle'), entity_id ('switch.xxx', etc.). "
                "Entity ID must be obtained using the list_homeassistant_states tool and not guessed."
            ),
            func=self._control_device_for_tool,
            args_schema=self.ToolSchema,
        )

    def _control_device_for_tool(self, action: str, entity_id: str) -> dict[str, Any] | str:
        """Function called by the agent.

        -> Internally calls _control_device.

        Args:
            action: Action to perform (turn_on, turn_off, toggle).
            entity_id: Entity ID to control.

        Returns:
            dict or str: Control result or error message.
        """
        logger.info(i18n.t('components.homeassistant.home_assistant_control.logs.tool_invoked',
                           action=action,
                           entity_id=entity_id))

        return self._control_device(
            ha_token=self.ha_token,
            base_url=self.base_url,
            action=action,
            entity_id=entity_id,
        )

    def _control_device(
        self,
        ha_token: str,
        base_url: str,
        action: str,
        entity_id: str,
    ) -> dict[str, Any] | str:
        """Actual logic to call the Home Assistant service.

        The domain is extracted from the beginning of the entity_id.
        Example: entity_id="switch.unknown_switch_3" -> domain="switch".

        Args:
            ha_token: Home Assistant access token.
            base_url: Home Assistant base URL.
            action: Action to perform (turn_on, turn_off, toggle).
            entity_id: Entity ID to control.

        Returns:
            dict or str: Home Assistant response or error message.
        """
        try:
            logger.debug(i18n.t('components.homeassistant.home_assistant_control.logs.extracting_domain',
                                entity_id=entity_id))

            domain = entity_id.split(".")[0]  # switch, light, cover, etc.
            url = f"{base_url}/api/services/{domain}/{action}"

            logger.debug(i18n.t('components.homeassistant.home_assistant_control.logs.calling_service',
                                url=url,
                                domain=domain,
                                action=action))

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            payload = {"entity_id": entity_id}

            response = requests.post(
                url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(i18n.t('components.homeassistant.home_assistant_control.logs.control_successful',
                               entity_id=entity_id,
                               action=action))

            return response.json()  # HA response JSON on success

        except requests.exceptions.Timeout as e:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.timeout',
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.ConnectionError as e:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.connection_failed',
                               base_url=base_url,
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.HTTPError as e:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.http_error',
                               status=response.status_code,
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except requests.exceptions.RequestException as e:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.request_failed',
                               error=str(e))
            logger.error(error_msg)
            return error_msg

        except IndexError:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.invalid_entity_format',
                               entity_id=entity_id)
            logger.error(error_msg)
            return error_msg

        except Exception as e:
            error_msg = i18n.t('components.homeassistant.home_assistant_control.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            return error_msg

    def _make_data_response(self, result: dict[str, Any] | str) -> Data:
        """Returns a response in the LangFlow Data format.

        Args:
            result: Control result (dict) or error message (str).

        Returns:
            Data: Formatted data response.
        """
        if isinstance(result, str):
            # Handle error messages
            logger.debug(i18n.t(
                'components.homeassistant.home_assistant_control.logs.returning_error_response'))
            return Data(text=result)

        # Convert dict to JSON string
        logger.debug(i18n.t(
            'components.homeassistant.home_assistant_control.logs.formatting_success_response'))
        formatted_json = json.dumps(result, indent=2, ensure_ascii=False)
        return Data(data=result, text=formatted_json)
