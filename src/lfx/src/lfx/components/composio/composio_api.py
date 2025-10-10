# Standard library imports
from collections.abc import Sequence
import os
from typing import Any

import i18n
from composio import Composio
from composio_langchain import LangchainProvider

# Third-party imports
from langchain_core.tools import Tool

# Local imports
from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.inputs.inputs import (
    ConnectionInput,
    MessageTextInput,
    SecretStrInput,
    SortableListInput,
)
from lfx.io import Output
from lfx.log.logger import logger

# TODO: We get the list from the API but we need to filter it
enabled_tools = ["confluence", "discord", "dropbox", "github",
                 "gmail", "linkedin", "notion", "slack", "youtube"]


class ComposioAPIComponent(LCToolComponent):
    display_name: str = i18n.t('components.composio.composio_api.display_name')
    description: str = i18n.t('components.composio.composio_api.description')
    name = "ComposioAPI"
    icon = "Composio"
    documentation: str = "https://docs.composio.dev"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        # Basic configuration inputs
        MessageTextInput(
            name="entity_id",
            display_name=i18n.t(
                'components.composio.composio_api.entity_id.display_name'),
            value="default",
            advanced=True
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.composio.composio_api.api_key.display_name'),
            required=True,
            info=i18n.t('components.composio.composio_api.api_key.info'),
            real_time_refresh=True,
        ),
        ConnectionInput(
            name="tool_name",
            display_name=i18n.t(
                'components.composio.composio_api.tool_name.display_name'),
            placeholder=i18n.t(
                'components.composio.composio_api.tool_name.placeholder'),
            button_metadata={"icon": "unplug", "variant": "destructive"},
            options=[],
            search_category=[],
            value="",
            connection_link="",
            info=i18n.t('components.composio.composio_api.tool_name.info'),
            real_time_refresh=True,
        ),
        SortableListInput(
            name="actions",
            display_name=i18n.t(
                'components.composio.composio_api.actions.display_name'),
            placeholder=i18n.t(
                'components.composio.composio_api.actions.placeholder'),
            helper_text=i18n.t(
                'components.composio.composio_api.actions.helper_text'),
            helper_text_metadata={
                "icon": "OctagonAlert", "variant": "destructive"},
            options=[],
            value="",
            info=i18n.t('components.composio.composio_api.actions.info'),
            limit=1,
            show=False,
        ),
    ]

    outputs = [
        Output(
            name="tools",
            display_name=i18n.t(
                'components.composio.composio_api.outputs.tools.display_name'),
            method="build_tool"
        ),
    ]

    def validate_tool(self, build_config: dict, field_value: Any, tool_name: str | None = None) -> dict:
        logger.debug(i18n.t('components.composio.composio_api.logs.validating_tool',
                            tool_name=tool_name or field_value))

        # Get the index of the selected tool in the list of options
        selected_tool_index = next(
            (
                ind
                for ind, tool in enumerate(build_config["tool_name"]["options"])
                if tool["name"] == field_value
                or ("validate" in field_value and tool["name"] == field_value["validate"])
            ),
            None,
        )

        # Set the link to be the text 'validated'
        if selected_tool_index is not None:
            build_config["tool_name"]["options"][selected_tool_index]["link"] = "validated"
            logger.debug(i18n.t('components.composio.composio_api.logs.tool_validated',
                                index=selected_tool_index))

        # Set the helper text and helper text metadata field of the actions now
        build_config["actions"]["helper_text"] = ""
        build_config["actions"]["helper_text_metadata"] = {
            "icon": "Check", "variant": "success"}

        try:
            composio = self._build_wrapper()
            current_tool = tool_name or getattr(self, "tool_name", None)
            if not current_tool:
                warning_msg = i18n.t(
                    'components.composio.composio_api.warnings.no_tool_name')
                logger.warning(warning_msg)
                self.log(warning_msg)
                return build_config

            toolkit_slug = current_tool.lower()
            logger.info(i18n.t('components.composio.composio_api.logs.getting_actions',
                               toolkit=toolkit_slug))

            tools = composio.tools.get(
                user_id=self.entity_id, toolkits=[toolkit_slug])

            authenticated_actions = []
            for tool in tools:
                if hasattr(tool, "name"):
                    action_name = tool.name
                    display_name = action_name.replace("_", " ").title()
                    authenticated_actions.append(
                        {"name": action_name, "display_name": display_name})

            logger.info(i18n.t('components.composio.composio_api.logs.actions_retrieved',
                               count=len(authenticated_actions),
                               toolkit=toolkit_slug))

        except (ValueError, ConnectionError, AttributeError) as e:
            error_msg = i18n.t('components.composio.composio_api.errors.get_actions_failed',
                               tool=current_tool or 'unknown tool',
                               error=str(e))
            logger.exception(error_msg)
            self.log(error_msg)
            authenticated_actions = []

        build_config["actions"]["options"] = [
            {
                "name": action["name"],
            }
            for action in authenticated_actions
        ]

        build_config["actions"]["show"] = True
        logger.debug(i18n.t('components.composio.composio_api.logs.actions_config_updated',
                            count=len(authenticated_actions)))
        return build_config

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        logger.debug(i18n.t('components.composio.composio_api.logs.updating_config',
                            field_name=field_name or 'unknown'))

        if field_name == "api_key" or (self.api_key and not build_config["tool_name"]["options"]):
            if field_name == "api_key" and not field_value:
                logger.info(
                    i18n.t('components.composio.composio_api.logs.clearing_config'))

                build_config["tool_name"]["options"] = []
                build_config["tool_name"]["value"] = ""

                # Reset the list of actions
                build_config["actions"]["show"] = False
                build_config["actions"]["options"] = []
                build_config["actions"]["value"] = ""

                return build_config

            # Build the list of available tools
            logger.info(
                i18n.t('components.composio.composio_api.logs.building_tool_list'))

            build_config["tool_name"]["options"] = [
                {
                    "name": app.title(),
                    "icon": app,
                    "link": (
                        build_config["tool_name"]["options"][ind]["link"]
                        if build_config["tool_name"]["options"]
                        else ""
                    ),
                }
                for ind, app in enumerate(enabled_tools)
            ]

            logger.info(i18n.t('components.composio.composio_api.logs.tool_list_built',
                               count=len(enabled_tools)))

            return build_config

        if field_name == "tool_name" and field_value:
            composio = self._build_wrapper()

            current_tool_name = (
                field_value
                if isinstance(field_value, str)
                else field_value.get("validate")
                if isinstance(field_value, dict) and "validate" in field_value
                else getattr(self, "tool_name", None)
            )

            if not current_tool_name:
                warning_msg = i18n.t(
                    'components.composio.composio_api.warnings.no_tool_name_connection')
                logger.warning(warning_msg)
                self.log(warning_msg)
                return build_config

            try:
                toolkit_slug = current_tool_name.lower()
                logger.info(i18n.t('components.composio.composio_api.logs.checking_connection',
                                   toolkit=toolkit_slug))

                connection_list = composio.connected_accounts.list(
                    user_ids=[self.entity_id], toolkit_slugs=[toolkit_slug]
                )

                # Check for active connections
                has_active_connections = False
                if (
                    connection_list
                    and hasattr(connection_list, "items")
                    and connection_list.items
                    and isinstance(connection_list.items, list)
                    and len(connection_list.items) > 0
                ):
                    for connection in connection_list.items:
                        if getattr(connection, "status", None) == "ACTIVE":
                            has_active_connections = True
                            break

                # Get the index of the selected tool in the list of options
                selected_tool_index = next(
                    (
                        ind
                        for ind, tool in enumerate(build_config["tool_name"]["options"])
                        if tool["name"] == current_tool_name.title()
                    ),
                    None,
                )

                if has_active_connections:
                    # User has active connection
                    logger.info(i18n.t('components.composio.composio_api.logs.active_connection_found',
                                       toolkit=toolkit_slug))

                    if selected_tool_index is not None:
                        build_config["tool_name"]["options"][selected_tool_index]["link"] = "validated"

                    # If it's a validation request, validate the tool
                    if (isinstance(field_value, dict) and "validate" in field_value) or isinstance(field_value, str):
                        return self.validate_tool(build_config, field_value, current_tool_name)
                else:
                    # No active connection - create OAuth connection
                    logger.info(i18n.t('components.composio.composio_api.logs.no_active_connection',
                                       toolkit=toolkit_slug))

                    try:
                        connection = composio.toolkits.authorize(
                            user_id=self.entity_id, toolkit=toolkit_slug)
                        redirect_url = getattr(
                            connection, "redirect_url", None)

                        if redirect_url and redirect_url.startswith(("http://", "https://")):
                            if selected_tool_index is not None:
                                build_config["tool_name"]["options"][selected_tool_index]["link"] = redirect_url
                                logger.info(i18n.t('components.composio.composio_api.logs.oauth_link_created',
                                                   toolkit=toolkit_slug))
                        elif selected_tool_index is not None:
                            build_config["tool_name"]["options"][selected_tool_index]["link"] = "error"
                            logger.warning(i18n.t('components.composio.composio_api.warnings.invalid_redirect_url',
                                                  toolkit=toolkit_slug))
                    except (ValueError, ConnectionError, AttributeError) as e:
                        error_msg = i18n.t('components.composio.composio_api.errors.oauth_creation_failed',
                                           error=str(e))
                        logger.exception(error_msg)
                        self.log(error_msg)
                        if selected_tool_index is not None:
                            build_config["tool_name"]["options"][selected_tool_index]["link"] = "error"

            except (ValueError, ConnectionError, AttributeError) as e:
                error_msg = i18n.t('components.composio.composio_api.errors.connection_check_failed',
                                   error=str(e))
                logger.exception(error_msg)
                self.log(error_msg)

        return build_config

    def build_tool(self) -> Sequence[Tool]:
        """Build Composio tools based on selected actions.

        Returns:
            Sequence[Tool]: List of configured Composio tools.
        """
        try:
            logger.info(
                i18n.t('components.composio.composio_api.logs.building_tools'))

            composio = self._build_wrapper()
            action_names = [action["name"] for action in self.actions]

            logger.debug(i18n.t('components.composio.composio_api.logs.actions_selected',
                                count=len(action_names)))

            # Get toolkits from action names
            toolkits = set()
            for action_name in action_names:
                if "_" in action_name:
                    toolkit = action_name.split("_")[0].lower()
                    toolkits.add(toolkit)

            if not toolkits:
                warning_msg = i18n.t(
                    'components.composio.composio_api.warnings.no_toolkits')
                logger.warning(warning_msg)
                self.status = warning_msg
                return []

            logger.info(i18n.t('components.composio.composio_api.logs.toolkits_identified',
                               count=len(toolkits),
                               toolkits=list(toolkits)))

            # Get all tools for the relevant toolkits
            all_tools = composio.tools.get(
                user_id=self.entity_id, toolkits=list(toolkits))

            # Filter to only the specific actions we want using list comprehension
            filtered_tools = [tool for tool in all_tools if hasattr(
                tool, "name") and tool.name in action_names]

            success_msg = i18n.t('components.composio.composio_api.status.tools_built',
                                 count=len(filtered_tools))
            self.status = success_msg
            logger.info(success_msg)

            return filtered_tools

        except Exception as e:
            error_msg = i18n.t('components.composio.composio_api.errors.build_tools_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _build_wrapper(self) -> Composio:
        """Build the Composio wrapper using new SDK.

        Returns:
            Composio: The initialized Composio client.

        Raises:
            ValueError: If the API key is not found or invalid.
        """
        try:
            if not self.api_key:
                error_msg = i18n.t(
                    'components.composio.composio_api.errors.api_key_required')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(
                i18n.t('components.composio.composio_api.logs.building_wrapper'))
            composio = Composio(api_key=self.api_key,
                                provider=LangchainProvider())
            logger.info(
                i18n.t('components.composio.composio_api.logs.wrapper_built'))

            return composio

        except ValueError as e:
            error_msg = i18n.t('components.composio.composio_api.errors.wrapper_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.log(error_msg)

            invalid_key_msg = i18n.t(
                'components.composio.composio_api.errors.invalid_api_key')
            raise ValueError(invalid_key_msg) from e
