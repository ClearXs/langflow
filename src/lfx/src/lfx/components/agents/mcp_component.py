from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any
import i18n

from langchain_core.tools import StructuredTool  # noqa: TC002

from lfx.base.agents.utils import maybe_unflatten_dict, safe_cache_get, safe_cache_set
from lfx.base.mcp.util import (
    MCPStdioClient,
    MCPStreamableHttpClient,
    create_input_schema_from_json_schema,
    update_tools,
)
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.inputs.inputs import InputTypes  # noqa: TC001
from lfx.io import BoolInput, DropdownInput, McpInput, MessageTextInput, Output
from lfx.io.schema import flatten_schema, schema_to_langflow_inputs
from lfx.log.logger import logger
from lfx.schema.dataframe import DataFrame
from lfx.schema.message import Message
from lfx.services.deps import get_settings_service, get_storage_service, session_scope


class MCPToolsComponent(ComponentWithCache):
    schema_inputs: list = []
    tools: list[StructuredTool] = []
    _not_load_actions: bool = False
    _tool_cache: dict = {}
    _last_selected_server: str | None = None  # Cache for the last selected server

    def __init__(self, **data) -> None:
        super().__init__(**data)
        # Initialize cache keys to avoid CacheMiss when accessing them
        self._ensure_cache_structure()

        # Initialize clients with access to the component cache
        self.stdio_client: MCPStdioClient = MCPStdioClient(
            component_cache=self._shared_component_cache)
        self.streamable_http_client: MCPStreamableHttpClient = MCPStreamableHttpClient(
            component_cache=self._shared_component_cache
        )

    def _ensure_cache_structure(self):
        """Ensure the cache has the required structure."""
        try:
            # Check if servers key exists and is not CacheMiss
            servers_value = safe_cache_get(
                self._shared_component_cache, "servers")
            if servers_value is None:
                safe_cache_set(self._shared_component_cache, "servers", {})

            # Check if last_selected_server key exists and is not CacheMiss
            last_server_value = safe_cache_get(
                self._shared_component_cache, "last_selected_server")
            if last_server_value is None:
                safe_cache_set(self._shared_component_cache,
                               "last_selected_server", "")

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.cache_structure_init_failed', error=str(e))
            logger.warning(error_msg)

    default_keys: list[str] = [
        "code",
        "_type",
        "tool_mode",
        "tool_placeholder",
        "mcp_server",
        "tool",
        "use_cache",
    ]

    display_name = i18n.t('components.agents.mcp_component.display_name')
    description = i18n.t('components.agents.mcp_component.description')
    documentation: str = "https://docs.langflow.org/mcp-client"
    icon = "Mcp"
    name = "MCPTools"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        McpInput(
            name="mcp_server",
            display_name=i18n.t(
                'components.agents.mcp_component.mcp_server.display_name'),
            info=i18n.t('components.agents.mcp_component.mcp_server.info'),
            real_time_refresh=True,
        ),
        BoolInput(
            name="use_cache",
            display_name="Use Cached Server",
            info=(
                "Enable caching of MCP Server and tools to improve performance. "
                "Disable to always fetch fresh tools and server updates."
            ),
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="tool",
            display_name=i18n.t(
                'components.agents.mcp_component.tool.display_name'),
            options=[],
            value="",
            info=i18n.t('components.agents.mcp_component.tool.info'),
            show=False,
            required=True,
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="tool_placeholder",
            display_name=i18n.t(
                'components.agents.mcp_component.tool_placeholder.display_name'),
            info=i18n.t(
                'components.agents.mcp_component.tool_placeholder.info'),
            value="",
            show=False,
            tool_mode=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.agents.mcp_component.outputs.response.display_name'),
            name="response",
            method="build_output"
        ),
    ]

    async def _validate_schema_inputs(self, tool_obj) -> list[InputTypes]:
        """Validate and process schema inputs for a tool."""
        try:
            if not tool_obj or not hasattr(tool_obj, "args_schema"):
                error_msg = i18n.t(
                    'components.agents.mcp_component.errors.invalid_tool_object')
                raise ValueError(error_msg)

            flat_schema = flatten_schema(tool_obj.args_schema.schema())
            input_schema = create_input_schema_from_json_schema(flat_schema)
            if not input_schema:
                error_msg = i18n.t(
                    'components.agents.mcp_component.errors.empty_input_schema', tool_name=tool_obj.name)
                raise ValueError(error_msg)

            schema_inputs = schema_to_langflow_inputs(input_schema)
            if not schema_inputs:
                warning_msg = i18n.t(
                    'components.agents.mcp_component.warnings.no_input_parameters', tool_name=tool_obj.name)
                await logger.awarning(warning_msg)
                return []

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.schema_validation_failed', error=str(e))
            await logger.aexception(error_msg)
            raise ValueError(error_msg) from e
        else:
            return schema_inputs

    async def update_tool_list(self, mcp_server_value=None):
        """Update the list of available tools from MCP server."""
        try:
            # Accepts mcp_server_value as dict {name, config} or uses self.mcp_server
            mcp_server = mcp_server_value if mcp_server_value is not None else getattr(
                self, "mcp_server", None)
            server_name = None
            server_config_from_value = None
            if isinstance(mcp_server, dict):
                server_name = mcp_server.get("name")
                server_config_from_value = mcp_server.get("config")
            else:
                server_name = mcp_server
            if not server_name:
                self.tools = []
                return [], {"name": server_name, "config": server_config_from_value}

        # Check if caching is enabled, default to False
        use_cache = getattr(self, "use_cache", False)

        # Use shared cache if available and caching is enabled
        cached = None
        if use_cache:
            servers_cache = safe_cache_get(
                self._shared_component_cache, "servers", {})
            cached = servers_cache.get(server_name) if isinstance(
                servers_cache, dict) else None

        if cached is not None:
            try:
                self.tools = cached["tools"]
                self.tool_names = cached["tool_names"]
                self._tool_cache = cached["tool_cache"]
                server_config_from_value = cached["config"]
            except (TypeError, KeyError, AttributeError) as e:
                # Handle corrupted cache data by clearing it and continuing to fetch fresh tools
                msg = f"Unable to use cached data for MCP Server{server_name}: {e}"
                await logger.awarning(msg)
                # Clear the corrupted cache entry
                current_servers_cache = safe_cache_get(
                    self._shared_component_cache, "servers", {})
                if isinstance(current_servers_cache, dict) and server_name in current_servers_cache:
                    current_servers_cache.pop(server_name)
                    safe_cache_set(self._shared_component_cache,
                                   "servers", current_servers_cache)
            else:
                return self.tools, {"name": server_name, "config": server_config_from_value}

            try:
                try:
                    from langflow.api.v2.mcp import get_server
                    from langflow.services.database.models.user.crud import get_user_by_id
                except ImportError as e:
                    error_msg = i18n.t(
                        'components.agents.mcp_component.errors.langflow_mcp_not_available')
                    raise ImportError(error_msg) from e

                async with session_scope() as db:
                    if not self.user_id:
                        error_msg = i18n.t(
                            'components.agents.mcp_component.errors.user_id_required')
                        raise ValueError(error_msg)
                    current_user = await get_user_by_id(db, self.user_id)

                    # Try to get server config from DB/API
                    server_config = await get_server(
                        server_name,
                        current_user,
                        db,
                        storage_service=get_storage_service(),
                        settings_service=get_settings_service(),
                    )

                # If get_server returns empty but we have a config, use it
                if not server_config and server_config_from_value:
                    server_config = server_config_from_value

                if not server_config:
                    warning_msg = i18n.t('components.agents.mcp_component.warnings.no_server_config',
                                         server_name=server_name)
                    await logger.awarning(warning_msg)
                    self.tools = []
                    return [], {"name": server_name, "config": server_config}

            _, tool_list, tool_cache = await update_tools(
                server_name=server_name,
                server_config=server_config,
                mcp_stdio_client=self.stdio_client,
                mcp_streamable_http_client=self.streamable_http_client,
            )

            self.tool_names = [
                tool.name for tool in tool_list if hasattr(tool, "name")]
            self._tool_cache = tool_cache
            self.tools = tool_list

            # Cache the result only if caching is enabled
            if use_cache:
                cache_data = {
                    "tools": tool_list,
                    "tool_names": self.tool_names,
                    "tool_cache": tool_cache,
                    "config": server_config,
                }

                # Safely update the servers cache
                current_servers_cache = safe_cache_get(
                    self._shared_component_cache, "servers", {})
                if isinstance(current_servers_cache, dict):
                    current_servers_cache[server_name] = cache_data
                    safe_cache_set(self._shared_component_cache,
                                   "servers", current_servers_cache)

            except (TimeoutError, asyncio.TimeoutError) as e:
                error_msg = i18n.t(
                    'components.agents.mcp_component.errors.timeout_updating_tools', error=str(e))
                await logger.aexception(error_msg)
                raise TimeoutError(error_msg) from e
            except Exception as e:
                error_msg = i18n.t(
                    'components.agents.mcp_component.errors.tool_update_failed', error=str(e))
                await logger.aexception(error_msg)
                raise ValueError(error_msg) from e
            else:
                return tool_list, {"name": server_name, "config": server_config}

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.update_tool_list_failed', error=str(e))
            await logger.aexception(error_msg)
            raise ValueError(error_msg) from e

    async def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Toggle the visibility of connection-specific fields based on the selected mode."""
        try:
            if field_name == "tool":
                try:
                    if len(self.tools) == 0:
                        try:
                            self.tools, build_config["mcp_server"]["value"] = await self.update_tool_list()
                            build_config["tool"]["options"] = [
                                tool.name for tool in self.tools]
                            build_config["tool"]["placeholder"] = i18n.t(
                                'components.agents.mcp_component.placeholders.select_tool')
                        except (TimeoutError, asyncio.TimeoutError) as e:
                            error_msg = i18n.t(
                                'components.agents.mcp_component.errors.timeout_updating_tools', error=str(e))
                            await logger.aexception(error_msg)
                            if not build_config["tools_metadata"]["show"]:
                                build_config["tool"]["show"] = True
                                build_config["tool"]["options"] = []
                                build_config["tool"]["value"] = ""
                                build_config["tool"]["placeholder"] = i18n.t(
                                    'components.agents.mcp_component.placeholders.timeout_mcp_server')
                            else:
                                build_config["tool"]["show"] = False
                        except ValueError:
                            if not build_config["tools_metadata"]["show"]:
                                build_config["tool"]["show"] = True
                                build_config["tool"]["options"] = []
                                build_config["tool"]["value"] = ""
                                build_config["tool"]["placeholder"] = i18n.t(
                                    'components.agents.mcp_component.placeholders.error_mcp_server')
                            else:
                                build_config["tool"]["show"] = False

                    if field_value == "":
                        return build_config

                    tool_obj = None
                    for tool in self.tools:
                        if tool.name == field_value:
                            tool_obj = tool
                            break
                    if tool_obj is None:
                        warning_msg = i18n.t('components.agents.mcp_component.warnings.tool_not_found',
                                             tool_name=field_value, available_tools=str(self.tools))
                        await logger.awarning(warning_msg)
                        return build_config
                    await self._update_tool_config(build_config, field_value)
                except Exception as e:
                    build_config["tool"]["options"] = []
                    error_msg = i18n.t(
                        'components.agents.mcp_component.errors.tools_update_failed', error=str(e))
                    raise ValueError(error_msg) from e
                else:
                    return build_config

            elif field_name == "mcp_server":
                if not field_value:
                    build_config["tool"]["show"] = False
                    build_config["tool"]["options"] = []
                    build_config["tool"]["value"] = ""
                    build_config["tool"]["placeholder"] = ""
                    build_config["tool_placeholder"]["tool_mode"] = False
                    self.remove_non_default_keys(build_config)
                    return build_config

                build_config["tool_placeholder"]["tool_mode"] = True

                current_server_name = field_value.get("name") if isinstance(
                    field_value, dict) else field_value
                _last_selected_server = safe_cache_get(
                    self._shared_component_cache, "last_selected_server", "")

                # To avoid unnecessary updates, only proceed if the server has actually changed
                if (_last_selected_server in (current_server_name, "")) and build_config["tool"]["show"]:
                    if current_server_name:
                        servers_cache = safe_cache_get(
                            self._shared_component_cache, "servers", {})
                        if isinstance(servers_cache, dict):
                            cached = servers_cache.get(current_server_name)
                            if cached is not None and cached.get("tool_names"):
                                cached_tools = cached["tool_names"]
                                current_tools = build_config["tool"]["options"]
                                if current_tools == cached_tools:
                                    return build_config
                    else:
                        return build_config

                # Determine if "Tool Mode" is active by checking if the tool dropdown is hidden.
                is_in_tool_mode = build_config["tools_metadata"]["show"]
                safe_cache_set(self._shared_component_cache,
                               "last_selected_server", current_server_name)

                # Check if tools are already cached for this server before clearing
                cached_tools = None
                if current_server_name:
                    use_cache = getattr(self, "use_cache", True)
                    if use_cache:
                        servers_cache = safe_cache_get(
                            self._shared_component_cache, "servers", {})
                        if isinstance(servers_cache, dict):
                            cached = servers_cache.get(current_server_name)
                            if cached is not None:
                                try:
                                    cached_tools = cached["tools"]
                                    self.tools = cached_tools
                                    self.tool_names = cached["tool_names"]
                                    self._tool_cache = cached["tool_cache"]
                                except (TypeError, KeyError, AttributeError) as e:
                                    # Handle corrupted cache data by ignoring it
                                    msg = f"Unable to use cached data for MCP Server,{current_server_name}: {e}"
                                    await logger.awarning(msg)
                                    cached_tools = None

                # Only clear tools if we don't have cached tools for the current server
                if not cached_tools:
                    self.tools = []  # Clear previous tools only if no cache

                # Clear previous tool inputs
                self.remove_non_default_keys(build_config)

                # Only show the tool dropdown if not in tool_mode
                if not is_in_tool_mode:
                    build_config["tool"]["show"] = True
                    if cached_tools:
                        # Use cached tools to populate options immediately
                        build_config["tool"]["options"] = [
                            tool.name for tool in cached_tools]
                        build_config["tool"]["placeholder"] = i18n.t(
                            'components.agents.mcp_component.placeholders.select_tool')
                    else:
                        # Show loading state only when we need to fetch tools
                        build_config["tool"]["placeholder"] = i18n.t(
                            'components.agents.mcp_component.placeholders.loading_tools')
                        build_config["tool"]["options"] = []
                    build_config["tool"]["value"] = uuid.uuid4()
                else:
                    # Keep the tool dropdown hidden if in tool_mode
                    self._not_load_actions = True
                    build_config["tool"]["show"] = False

            elif field_name == "tool_mode":
                build_config["tool"]["placeholder"] = ""
                build_config["tool"]["show"] = not bool(
                    field_value) and bool(build_config["mcp_server"])
                self.remove_non_default_keys(build_config)
                self.tool = build_config["tool"]["value"]
                if field_value:
                    self._not_load_actions = True
                else:
                    build_config["tool"]["value"] = uuid.uuid4()
                    build_config["tool"]["options"] = []
                    build_config["tool"]["show"] = True
                    build_config["tool"]["placeholder"] = i18n.t(
                        'components.agents.mcp_component.placeholders.loading_tools')
            elif field_name == "tools_metadata":
                self._not_load_actions = False

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.build_config_update_failed', error=str(e))
            await logger.aexception(error_msg)
            raise ValueError(error_msg) from e
        else:
            return build_config

    def get_inputs_for_all_tools(self, tools: list) -> dict:
        """Get input schemas for all tools."""
        try:
            inputs = {}
            for tool in tools:
                if not tool or not hasattr(tool, "name"):
                    continue
                try:
                    flat_schema = flatten_schema(tool.args_schema.schema())
                    input_schema = create_input_schema_from_json_schema(
                        flat_schema)
                    langflow_inputs = schema_to_langflow_inputs(input_schema)
                    inputs[tool.name] = langflow_inputs
                except (AttributeError, ValueError, TypeError, KeyError) as e:
                    error_msg = i18n.t('components.agents.mcp_component.errors.tool_input_schema_failed',
                                       tool_name=getattr(tool, 'name', 'unknown'), error=str(e))
                    logger.exception(error_msg)
                    continue
            return inputs

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.get_inputs_for_tools_failed', error=str(e))
            logger.exception(error_msg)
            return {}

    def remove_input_schema_from_build_config(
        self, build_config: dict, tool_name: str, input_schema: dict[list[InputTypes], Any]
    ):
        """Remove the input schema for the tool from the build config."""
        try:
            # Keep only schemas that don't belong to the current tool
            input_schema = {k: v for k,
                            v in input_schema.items() if k != tool_name}
            # Remove all inputs from other tools
            for value in input_schema.values():
                for _input in value:
                    if _input.name in build_config:
                        build_config.pop(_input.name)

        except Exception as e:
            error_msg = i18n.t('components.agents.mcp_component.errors.remove_input_schema_failed',
                               tool_name=tool_name, error=str(e))
            logger.warning(error_msg)

    def remove_non_default_keys(self, build_config: dict) -> None:
        """Remove non-default keys from the build config."""
        try:
            for key in list(build_config.keys()):
                if key not in self.default_keys:
                    build_config.pop(key)

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.remove_non_default_keys_failed', error=str(e))
            logger.warning(error_msg)

    async def _update_tool_config(self, build_config: dict, tool_name: str) -> None:
        """Update tool configuration with proper error handling."""
        try:
            if not self.tools:
                self.tools, build_config["mcp_server"]["value"] = await self.update_tool_list()

            if not tool_name:
                return

            tool_obj = next(
                (tool for tool in self.tools if tool.name == tool_name), None)
            if not tool_obj:
                warning_msg = i18n.t('components.agents.mcp_component.warnings.tool_not_found_in_config',
                                     tool_name=tool_name, available_tools=str(self.tools))
                self.remove_non_default_keys(build_config)
                build_config["tool"]["value"] = ""
                await logger.awarning(warning_msg)
                return

            try:
                # Store current values before removing inputs
                current_values = {}
                for key, value in build_config.items():
                    if key not in self.default_keys and isinstance(value, dict) and "value" in value:
                        current_values[key] = value["value"]

                # Get all tool inputs and remove old ones
                input_schema_for_all_tools = self.get_inputs_for_all_tools(
                    self.tools)
                self.remove_input_schema_from_build_config(
                    build_config, tool_name, input_schema_for_all_tools)

                # Get and validate new inputs
                self.schema_inputs = await self._validate_schema_inputs(tool_obj)
                if not self.schema_inputs:
                    info_msg = i18n.t(
                        'components.agents.mcp_component.info.no_input_parameters', tool_name=tool_name)
                    await logger.ainfo(info_msg)
                    return

                # Add new inputs to build config
                for schema_input in self.schema_inputs:
                    if not schema_input or not hasattr(schema_input, "name"):
                        warning_msg = i18n.t(
                            'components.agents.mcp_component.warnings.invalid_schema_input')
                        await logger.awarning(warning_msg)
                        continue

                    try:
                        name = schema_input.name
                        input_dict = schema_input.to_dict()
                        input_dict.setdefault("value", None)
                        input_dict.setdefault("required", True)

                        build_config[name] = input_dict

                        # Preserve existing value if the parameter name exists in current_values
                        if name in current_values:
                            build_config[name]["value"] = current_values[name]

                    except (AttributeError, KeyError, TypeError) as e:
                        error_msg = i18n.t('components.agents.mcp_component.errors.schema_input_processing_failed',
                                           schema_input=str(schema_input), error=str(e))
                        await logger.aexception(error_msg)
                        continue

            except ValueError as e:
                error_msg = i18n.t('components.agents.mcp_component.errors.tool_schema_validation_failed',
                                   tool_name=tool_name, error=str(e))
                await logger.aexception(error_msg)
                self.schema_inputs = []
                return
            except (AttributeError, KeyError, TypeError) as e:
                error_msg = i18n.t(
                    'components.agents.mcp_component.errors.tool_config_update_failed', error=str(e))
                await logger.aexception(error_msg)
                raise ValueError(error_msg) from e

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.update_tool_config_failed', error=str(e))
            await logger.aexception(error_msg)
            raise ValueError(error_msg) from e

    async def build_output(self) -> DataFrame:
        """Build output with improved error handling and validation."""
        try:
            self.tools, _ = await self.update_tool_list()
            if self.tool != "":
                # Set session context for persistent MCP sessions using Langflow session ID
                session_context = self._get_session_context()
                if session_context:
                    self.stdio_client.set_session_context(session_context)
                    self.streamable_http_client.set_session_context(
                        session_context)

                exec_tool = self._tool_cache[self.tool]
                tool_args = self.get_inputs_for_all_tools(self.tools)[
                    self.tool]
                kwargs = {}
                for arg in tool_args:
                    value = getattr(self, arg.name, None)
                    if value is not None:
                        if isinstance(value, Message):
                            kwargs[arg.name] = value.text
                        else:
                            kwargs[arg.name] = value

                unflattened_kwargs = maybe_unflatten_dict(kwargs)

                output = await exec_tool.coroutine(**unflattened_kwargs)

                tool_content = []
                for item in output.content:
                    item_dict = item.model_dump()
                    tool_content.append(item_dict)

                success_msg = i18n.t('components.agents.mcp_component.success.tool_executed',
                                     tool_name=self.tool, result_count=len(tool_content))
                await logger.ainfo(success_msg)

                return DataFrame(data=tool_content)

            error_msg = i18n.t(
                'components.agents.mcp_component.errors.no_tool_selected')
            return DataFrame(data=[{"error": error_msg}])

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.build_output_failed', error=str(e))
            await logger.aexception(error_msg)
            raise ValueError(error_msg) from e

    def _get_session_context(self) -> str | None:
        """Get the Langflow session ID for MCP session caching."""
        try:
            # Try to get session ID from the component's execution context
            if hasattr(self, "graph") and hasattr(self.graph, "session_id"):
                session_id = self.graph.session_id
                # Include server name to ensure different servers get different sessions
                server_name = ""
                mcp_server = getattr(self, "mcp_server", None)
                if isinstance(mcp_server, dict):
                    server_name = mcp_server.get("name", "")
                elif mcp_server:
                    server_name = str(mcp_server)
                return f"{session_id}_{server_name}" if session_id else None
            return None

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.session_context_failed', error=str(e))
            logger.warning(error_msg)
            return None

    async def _get_tools(self):
        """Get cached tools or update if necessary."""
        try:
            mcp_server = getattr(self, "mcp_server", None)
            if not self._not_load_actions:
                tools, _ = await self.update_tool_list(mcp_server)
                return tools
            return []

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.mcp_component.errors.get_tools_failed', error=str(e))
            await logger.aexception(error_msg)
            return []
