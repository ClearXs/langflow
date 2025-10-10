import json
import os
import re
import i18n

from langchain_core.tools import StructuredTool, Tool
from pydantic import ValidationError

from lfx.base.agents.agent import LCToolsAgentComponent
from lfx.base.agents.events import ExceptionWithMessageError
from lfx.base.models.model_input_constants import (
    ALL_PROVIDER_FIELDS,
    MODEL_DYNAMIC_UPDATE_FIELDS,
    MODEL_PROVIDERS_DICT,
    MODELS_METADATA,
)
from lfx.base.models.model_utils import get_model_name
from lfx.components.helpers.current_date import CurrentDateComponent
from lfx.components.helpers.memory import MemoryComponent
from lfx.components.langchain_utilities.tool_calling import ToolCallingAgentComponent
from lfx.custom.custom_component.component import get_component_toolkit
from lfx.custom.utils import update_component_build_config
from lfx.helpers.base_model import build_model_from_schema
from lfx.inputs.inputs import BoolInput
from lfx.io import DropdownInput, IntInput, MultilineInput, Output, TableInput
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dotdict import dotdict
from lfx.schema.message import Message
from lfx.schema.table import EditMode


def set_advanced_true(component_input):
    component_input.advanced = True
    return component_input


MODEL_PROVIDERS_LIST = ["Anthropic", "Google Generative AI", "OpenAI"]


class AgentComponent(ToolCallingAgentComponent):
    display_name: str = i18n.t('components.agents.agent.display_name')
    description: str = i18n.t('components.agents.agent.description')
    documentation: str = "https://docs.langflow.org/agents"
    icon = "bot"
    beta = False
    name = "Agent"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    memory_inputs = [set_advanced_true(component_input)
                     for component_input in MemoryComponent().inputs]

    # Filter out json_mode from OpenAI inputs since we handle structured output differently
    if "OpenAI" in MODEL_PROVIDERS_DICT:
        openai_inputs_filtered = [
            input_field
            for input_field in MODEL_PROVIDERS_DICT["OpenAI"]["inputs"]
            if not (hasattr(input_field, "name") and input_field.name == "json_mode")
        ]
    else:
        openai_inputs_filtered = []

    inputs = [
        DropdownInput(
            name="agent_llm",
            display_name=i18n.t(
                'components.agents.agent.agent_llm.display_name'),
            info=i18n.t('components.agents.agent.agent_llm.info'),
            options=[*MODEL_PROVIDERS_LIST],
            value="OpenAI",
            real_time_refresh=True,
            refresh_button=False,
            input_types=[],
            options_metadata=[MODELS_METADATA[key]
                              for key in MODEL_PROVIDERS_LIST if key in MODELS_METADATA]
            + [{"icon": "brain"}],
            external_options={
                "fields": {
                    "data": {
                        "node": {
                            "name": "connect_other_models",
                            "display_name": i18n.t('components.agents.agent.connect_other_models.display_name'),
                            "icon": "CornerDownLeft",
                        }
                    }
                },
            },
        ),
        *openai_inputs_filtered,
        MultilineInput(
            name="system_prompt",
            display_name=i18n.t(
                'components.agents.agent.system_prompt.display_name'),
            info=i18n.t('components.agents.agent.system_prompt.info'),
            value=i18n.t(
                'components.agents.agent.system_prompt.default_value'),
            advanced=False,
        ),
        IntInput(
            name="n_messages",
            display_name=i18n.t(
                'components.agents.agent.n_messages.display_name'),
            value=100,
            info=i18n.t('components.agents.agent.n_messages.info'),
            advanced=True,
            show=True,
        ),
        MultilineInput(
            name="format_instructions",
            display_name=i18n.t(
                'components.agents.agent.format_instructions.display_name'),
            info=i18n.t('components.agents.agent.format_instructions.info'),
            value=i18n.t(
                'components.agents.agent.format_instructions.default_value'),
            advanced=True,
        ),
        TableInput(
            name="output_schema",
            display_name=i18n.t(
                'components.agents.agent.output_schema.display_name'),
            info=i18n.t('components.agents.agent.output_schema.info'),
            advanced=True,
            required=False,
            value=[],
            table_schema=[
                {
                    "name": "name",
                    "display_name": i18n.t('components.agents.agent.table_schema.name.display_name'),
                    "type": "str",
                    "description": i18n.t('components.agents.agent.table_schema.name.description'),
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": i18n.t('components.agents.agent.table_schema.description.display_name'),
                    "type": "str",
                    "description": i18n.t('components.agents.agent.table_schema.description.description'),
                    "default": i18n.t('components.agents.agent.table_schema.description.default'),
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "type",
                    "display_name": i18n.t('components.agents.agent.table_schema.type.display_name'),
                    "type": "str",
                    "edit_mode": EditMode.INLINE,
                    "description": i18n.t('components.agents.agent.table_schema.type.description'),
                    "options": ["str", "int", "float", "bool", "dict"],
                    "default": "str",
                },
                {
                    "name": "multiple",
                    "display_name": i18n.t('components.agents.agent.table_schema.multiple.display_name'),
                    "type": "boolean",
                    "description": i18n.t('components.agents.agent.table_schema.multiple.description'),
                    "default": "False",
                    "edit_mode": EditMode.INLINE,
                },
            ],
        ),
        *LCToolsAgentComponent.get_base_inputs(),
        # removed memory inputs from agent component
        # *memory_inputs,
        BoolInput(
            name="add_current_date_tool",
            display_name=i18n.t(
                'components.agents.agent.add_current_date_tool.display_name'),
            advanced=True,
            info=i18n.t('components.agents.agent.add_current_date_tool.info'),
            value=True,
        ),
    ]
    outputs = [
        Output(name="response", display_name=i18n.t(
            'components.agents.agent.outputs.response.display_name'), method="message_response"),
    ]

    async def get_agent_requirements(self):
        """Get the agent requirements for the agent."""
        try:
            llm_model, display_name = await self.get_llm()
            if llm_model is None:
                error_msg = i18n.t(
                    'components.agents.agent.errors.no_language_model')
                raise ValueError(error_msg)

            self.model_name = get_model_name(
                llm_model, display_name=display_name)

            # Get memory data
            self.chat_history = await self.get_memory_data()
            if isinstance(self.chat_history, Message):
                self.chat_history = [self.chat_history]

            # Add current date tool if enabled
            if self.add_current_date_tool:
                if not isinstance(self.tools, list):  # type: ignore[has-type]
                    self.tools = []
                current_date_tool = (await CurrentDateComponent(**self.get_base_args()).to_toolkit()).pop(0)
                if not isinstance(current_date_tool, StructuredTool):
                    error_msg = i18n.t(
                        'components.agents.agent.errors.current_date_tool_invalid')
                    raise TypeError(error_msg)
                self.tools.append(current_date_tool)

            return llm_model, self.chat_history, self.tools

        except (ValueError, TypeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.agent_requirements_failed', error=str(e))
            await logger.aerror(error_msg)
            raise ValueError(error_msg) from e

    async def message_response(self) -> Message:
        try:
            self.status = i18n.t(
                'components.agents.agent.status.initializing_agent')
            llm_model, self.chat_history, self.tools = await self.get_agent_requirements()

            # Set up and run agent
            self.status = i18n.t(
                'components.agents.agent.status.setting_up_agent')
            self.set(
                llm=llm_model,
                tools=self.tools or [],
                chat_history=self.chat_history,
                input_value=self.input_value,
                system_prompt=self.system_prompt,
            )

            self.status = i18n.t(
                'components.agents.agent.status.creating_agent')
            agent = self.create_agent_runnable()

            self.status = i18n.t(
                'components.agents.agent.status.running_agent')
            result = await self.run_agent(agent)

            # Store result for potential JSON output
            self._agent_result = result

            success_msg = i18n.t(
                'components.agents.agent.success.agent_completed')
            self.status = success_msg

        except (ValueError, TypeError, KeyError) as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.agent_execution_failed', error=str(e))
            await logger.aerror(f"{type(e).__name__}: {e!s}")
            self.status = error_msg
            raise
        except ExceptionWithMessageError as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.exception_with_message', error=str(e))
            await logger.aerror(f"ExceptionWithMessageError occurred: {e}")
            self.status = error_msg
            raise
        # Avoid catching blind Exception; let truly unexpected exceptions propagate
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.unexpected_error', error=str(e))
            await logger.aerror(f"Unexpected error: {e!s}")
            self.status = error_msg
            raise
        else:
            return result

    def _preprocess_schema(self, schema):
        """Preprocess schema to ensure correct data types for build_model_from_schema."""
        try:
            processed_schema = []
            for field in schema:
                processed_field = {
                    "name": str(field.get("name", "field")),
                    "type": str(field.get("type", "str")),
                    "description": str(field.get("description", "")),
                    "multiple": field.get("multiple", False),
                }
                # Ensure multiple is handled correctly
                if isinstance(processed_field["multiple"], str):
                    processed_field["multiple"] = processed_field["multiple"].lower() in [
                        "true",
                        "1",
                        "t",
                        "y",
                        "yes",
                    ]
                processed_schema.append(processed_field)
            return processed_schema

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.schema_preprocessing_failed', error=str(e))
            logger.aerror(error_msg)
            raise ValueError(error_msg) from e

    async def build_structured_output_base(self, content: str):
        """Build structured output with optional BaseModel validation."""
        try:
            json_pattern = r"\{.*\}"
            schema_error_msg = i18n.t(
                'components.agents.agent.errors.try_setting_output_schema')

            # Try to parse content as JSON first
            json_data = None
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(json_pattern, content, re.DOTALL)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        return {"content": content, "error": schema_error_msg}
                else:
                    return {"content": content, "error": schema_error_msg}

            # If no output schema provided, return parsed JSON without validation
            if not hasattr(self, "output_schema") or not self.output_schema or len(self.output_schema) == 0:
                return json_data

            # Use BaseModel validation with schema
            try:
                processed_schema = self._preprocess_schema(self.output_schema)
                output_model = build_model_from_schema(processed_schema)

                # Validate against the schema
                if isinstance(json_data, list):
                    # Multiple objects
                    validated_objects = []
                    for i, item in enumerate(json_data):
                        try:
                            validated_obj = output_model.model_validate(item)
                            validated_objects.append(
                                validated_obj.model_dump())
                        except ValidationError as e:
                            validation_error_msg = i18n.t('components.agents.agent.errors.validation_error_item',
                                                          index=i, error=str(e))
                            await logger.aerror(validation_error_msg)
                            # Include invalid items with error info
                            validated_objects.append(
                                {"data": item, "validation_error": str(e)})
                    return validated_objects

                # Single object
                try:
                    validated_obj = output_model.model_validate(json_data)
                    # Return as list for consistency
                    return [validated_obj.model_dump()]
                except ValidationError as e:
                    validation_error_msg = i18n.t(
                        'components.agents.agent.errors.validation_error_single', error=str(e))
                    await logger.aerror(validation_error_msg)
                    return [{"data": json_data, "validation_error": str(e)}]

            except (TypeError, ValueError) as e:
                error_msg = i18n.t(
                    'components.agents.agent.errors.structured_output_build_failed', error=str(e))
                await logger.aerror(error_msg)
                # Fallback to parsed JSON without validation
                return json_data

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.structured_output_base_failed', error=str(e))
            await logger.aerror(error_msg)
            return {"content": content, "error": str(e)}

    async def json_response(self) -> Data:
        """Convert agent response to structured JSON Data output with schema validation."""
        # Always use structured chat agent for JSON response mode for better JSON formatting
        try:
            self.status = i18n.t(
                'components.agents.agent.status.building_structured_response')
            system_components = []

            # 1. Agent Instructions (system_prompt)
            agent_instructions = getattr(self, "system_prompt", "") or ""
            if agent_instructions:
                system_components.append(f"{agent_instructions}")

            # 2. Format Instructions
            format_instructions = getattr(
                self, "format_instructions", "") or ""
            if format_instructions:
                system_components.append(
                    f"{i18n.t('components.agents.agent.labels.format_instructions')}: {format_instructions}")

            # 3. Schema Information from BaseModel
            if hasattr(self, "output_schema") and self.output_schema and len(self.output_schema) > 0:
                try:
                    processed_schema = self._preprocess_schema(
                        self.output_schema)
                    output_model = build_model_from_schema(processed_schema)
                    schema_dict = output_model.model_json_schema()
                    schema_info = i18n.t('components.agents.agent.prompts.schema_extraction',
                                         schema=json.dumps(schema_dict, indent=2))
                    system_components.append(schema_info)
                except (ValidationError, ValueError, TypeError, KeyError) as e:
                    error_msg = i18n.t(
                        'components.agents.agent.errors.schema_build_for_prompt_failed', error=str(e))
                    await logger.aerror(error_msg, exc_info=True)

            # Combine all components
            combined_instructions = "\n\n".join(
                system_components) if system_components else ""

            self.status = i18n.t(
                'components.agents.agent.status.getting_agent_requirements_json')
            llm_model, self.chat_history, self.tools = await self.get_agent_requirements()

            self.status = i18n.t(
                'components.agents.agent.status.setting_up_structured_agent')
            self.set(
                llm=llm_model,
                tools=self.tools or [],
                chat_history=self.chat_history,
                input_value=self.input_value,
                system_prompt=combined_instructions,
            )

            # Create and run structured chat agent
            try:
                self.status = i18n.t(
                    'components.agents.agent.status.creating_structured_agent')
                structured_agent = self.create_agent_runnable()
            except (NotImplementedError, ValueError, TypeError) as e:
                error_msg = i18n.t(
                    'components.agents.agent.errors.structured_agent_creation_failed', error=str(e))
                await logger.aerror(error_msg)
                raise
            try:
                self.status = i18n.t(
                    'components.agents.agent.status.running_structured_agent')
                result = await self.run_agent(structured_agent)
            except (
                ExceptionWithMessageError,
                ValueError,
                TypeError,
                RuntimeError,
            ) as e:
                error_msg = i18n.t(
                    'components.agents.agent.errors.structured_agent_result_failed', error=str(e))
                await logger.aerror(error_msg)
                raise

            # Extract content from structured agent result
            if hasattr(result, "content"):
                content = result.content
            elif hasattr(result, "text"):
                content = result.text
            else:
                content = str(result)

        except (
            ExceptionWithMessageError,
            ValueError,
            TypeError,
            NotImplementedError,
            AttributeError,
        ) as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.structured_chat_agent_failed', error=str(e))
            await logger.aerror(error_msg)
            # Fallback to regular agent
            content_str = i18n.t(
                'components.agents.agent.errors.no_content_from_agent')
            return Data(data={"content": content_str, "error": str(e)})

        # Process with structured output validation
        try:
            self.status = i18n.t(
                'components.agents.agent.status.processing_structured_output')
            structured_output = await self.build_structured_output_base(content)

            # Handle different output formats
            if isinstance(structured_output, list) and structured_output:
                if len(structured_output) == 1:
                    success_msg = i18n.t(
                        'components.agents.agent.success.single_structured_output')
                    self.status = success_msg
                    return Data(data=structured_output[0])
                success_msg = i18n.t(
                    'components.agents.agent.success.multiple_structured_outputs', count=len(structured_output))
                self.status = success_msg
                return Data(data={"results": structured_output})
            if isinstance(structured_output, dict):
                success_msg = i18n.t(
                    'components.agents.agent.success.dict_structured_output')
                self.status = success_msg
                return Data(data=structured_output)

            fallback_msg = i18n.t(
                'components.agents.agent.status.using_content_fallback')
            self.status = fallback_msg
            return Data(data={"content": content})

        except (ValueError, TypeError) as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.structured_output_processing_failed', error=str(e))
            await logger.aerror(error_msg)
            self.status = error_msg
            return Data(data={"content": content, "error": str(e)})

    async def get_memory_data(self):
        # TODO: This is a temporary fix to avoid message duplication. We should develop a function for this.
        try:
            messages = (
                await MemoryComponent(**self.get_base_args())
                .set(
                    session_id=self.graph.session_id,
                    order="Ascending",
                    n_messages=self.n_messages,
                )
                .retrieve_messages()
            )
            return [
                message for message in messages if getattr(message, "id", None) != getattr(self.input_value, "id", None)
            ]
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.memory_data_retrieval_failed', error=str(e))
            await logger.aerror(error_msg)
            return []  # Return empty list as fallback

    async def get_llm(self):
        try:
            if not isinstance(self.agent_llm, str):
                return self.agent_llm, None

            provider_info = MODEL_PROVIDERS_DICT.get(self.agent_llm)
            if not provider_info:
                error_msg = i18n.t(
                    'components.agents.agent.errors.invalid_model_provider', provider=self.agent_llm)
                raise ValueError(error_msg)

            component_class = provider_info.get("component_class")
            display_name = component_class.display_name
            inputs = provider_info.get("inputs")
            prefix = provider_info.get("prefix", "")

            return self._build_llm_model(component_class, inputs, prefix), display_name

        except (AttributeError, ValueError, TypeError, RuntimeError) as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.llm_build_failed', provider=self.agent_llm, error=str(e))
            await logger.aerror(error_msg)
            final_error_msg = i18n.t(
                'components.agents.agent.errors.llm_initialization_failed', error=str(e))
            raise ValueError(final_error_msg) from e

    def _build_llm_model(self, component, inputs, prefix=""):
        try:
            model_kwargs = {}
            for input_ in inputs:
                if hasattr(self, f"{prefix}{input_.name}"):
                    model_kwargs[input_.name] = getattr(
                        self, f"{prefix}{input_.name}")
            return component.set(**model_kwargs).build_model()
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.model_build_failed', error=str(e))
            raise ValueError(error_msg) from e

    def set_component_params(self, component):
        try:
            provider_info = MODEL_PROVIDERS_DICT.get(self.agent_llm)
            if provider_info:
                inputs = provider_info.get("inputs")
                prefix = provider_info.get("prefix")
                # Filter out json_mode and only use attributes that exist on this component
                model_kwargs = {}
                for input_ in inputs:
                    if hasattr(self, f"{prefix}{input_.name}"):
                        model_kwargs[input_.name] = getattr(
                            self, f"{prefix}{input_.name}")

                return component.set(**model_kwargs)
            return component
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.component_params_set_failed', error=str(e))
            logger.aerror(error_msg)
            return component

    def delete_fields(self, build_config: dotdict, fields: dict | list[str]) -> None:
        """Delete specified fields from build_config."""
        try:
            for field in fields:
                build_config.pop(field, None)
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.field_deletion_failed', error=str(e))
            self.log(error_msg, "warning")

    def update_input_types(self, build_config: dotdict) -> dotdict:
        """Update input types for all fields in build_config."""
        try:
            for key, value in build_config.items():
                if isinstance(value, dict):
                    if value.get("input_types") is None:
                        build_config[key]["input_types"] = []
                elif hasattr(value, "input_types") and value.input_types is None:
                    value.input_types = []
            return build_config
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.input_types_update_failed', error=str(e))
            self.log(error_msg, "warning")
            return build_config

    async def update_build_config(
        self, build_config: dotdict, field_value: str, field_name: str | None = None
    ) -> dotdict:
        try:
            # Iterate over all providers in the MODEL_PROVIDERS_DICT
            # Existing logic for updating build_config
            if field_name in ("agent_llm",):
                build_config["agent_llm"]["value"] = field_value
                provider_info = MODEL_PROVIDERS_DICT.get(field_value)
                if provider_info:
                    component_class = provider_info.get("component_class")
                    if component_class and hasattr(component_class, "update_build_config"):
                        # Call the component class's update_build_config method
                        build_config = await update_component_build_config(
                            component_class, build_config, field_value, "model_name"
                        )

                provider_configs: dict[str, tuple[dict, list[dict]]] = {
                    provider: (
                        MODEL_PROVIDERS_DICT[provider]["fields"],
                        [
                            MODEL_PROVIDERS_DICT[other_provider]["fields"]
                            for other_provider in MODEL_PROVIDERS_DICT
                            if other_provider != provider
                        ],
                    )
                    for provider in MODEL_PROVIDERS_DICT
                }
                if field_value in provider_configs:
                    fields_to_add, fields_to_delete = provider_configs[field_value]

                    # Delete fields from other providers
                    for fields in fields_to_delete:
                        self.delete_fields(build_config, fields)

                    # Add provider-specific fields
                    if field_value == "OpenAI" and not any(field in build_config for field in fields_to_add):
                        build_config.update(fields_to_add)
                    else:
                        build_config.update(fields_to_add)
                    # Reset input types for agent_llm
                    build_config["agent_llm"]["input_types"] = []
                    build_config["agent_llm"]["display_name"] = i18n.t(
                        'components.agents.agent.agent_llm.display_name')
                elif field_value == "connect_other_models":
                    # Delete all provider fields
                    self.delete_fields(build_config, ALL_PROVIDER_FIELDS)
                    # # Update with custom component
                    custom_component = DropdownInput(
                        name="agent_llm",
                        display_name=i18n.t(
                            'components.agents.agent.custom_llm.display_name'),
                        info=i18n.t('components.agents.agent.custom_llm.info'),
                        options=[*MODEL_PROVIDERS_LIST],
                        real_time_refresh=True,
                        refresh_button=False,
                        input_types=["LanguageModel"],
                        placeholder=i18n.t(
                            'components.agents.agent.custom_llm.placeholder'),
                        options_metadata=[
                            MODELS_METADATA[key] for key in MODEL_PROVIDERS_LIST if key in MODELS_METADATA],
                        external_options={
                            "fields": {
                                "data": {
                                    "node": {
                                        "name": "connect_other_models",
                                        "display_name": i18n.t('components.agents.agent.connect_other_models.display_name'),
                                        "icon": "CornerDownLeft",
                                    },
                                }
                            },
                        },
                    )
                    build_config.update(
                        {"agent_llm": custom_component.to_dict()})
                # Update input types for all fields
                build_config = self.update_input_types(build_config)

                # Validate required keys
                default_keys = [
                    "code",
                    "_type",
                    "agent_llm",
                    "tools",
                    "input_value",
                    "add_current_date_tool",
                    "system_prompt",
                    "agent_description",
                    "max_iterations",
                    "handle_parsing_errors",
                    "verbose",
                ]
                missing_keys = [
                    key for key in default_keys if key not in build_config]
                if missing_keys:
                    error_msg = i18n.t(
                        'components.agents.agent.errors.missing_required_keys', keys=str(missing_keys))
                    raise ValueError(error_msg)

            if (
                isinstance(self.agent_llm, str)
                and self.agent_llm in MODEL_PROVIDERS_DICT
                and field_name in MODEL_DYNAMIC_UPDATE_FIELDS
            ):
                provider_info = MODEL_PROVIDERS_DICT.get(self.agent_llm)
                if provider_info:
                    component_class = provider_info.get("component_class")
                    component_class = self.set_component_params(
                        component_class)
                    prefix = provider_info.get("prefix")
                    if component_class and hasattr(component_class, "update_build_config"):
                        # Call each component class's update_build_config method
                        # remove the prefix from the field_name
                        if isinstance(field_name, str) and isinstance(prefix, str):
                            field_name = field_name.replace(prefix, "")
                        build_config = await update_component_build_config(
                            component_class, build_config, field_value, "model_name"
                        )
            return dotdict({k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in build_config.items()})

        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.build_config_update_failed', error=str(e))
            await logger.aerror(error_msg)
            raise ValueError(error_msg) from e

    async def _get_tools(self) -> list[Tool]:
        try:
            component_toolkit = get_component_toolkit()
            tools_names = self._build_tools_names()
            agent_description = self.get_tool_description()
            # TODO: Agent Description Depreciated Feature to be removed
            description = f"{agent_description}{tools_names}"
            tools = component_toolkit(component=self).get_tools(
                tool_name="Call_Agent",
                tool_description=description,
                callbacks=self.get_langchain_callbacks(),
            )
            if hasattr(self, "tools_metadata"):
                tools = component_toolkit(
                    component=self, metadata=self.tools_metadata).update_tools_metadata(tools=tools)
            return tools
        except Exception as e:
            error_msg = i18n.t(
                'components.agents.agent.errors.tools_retrieval_failed', error=str(e))
            await logger.aerror(error_msg)
            return []  # Return empty list as fallback
