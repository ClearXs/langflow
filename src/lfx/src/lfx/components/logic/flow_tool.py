from typing import Any, Dict, List, Optional, Union
import json
import asyncio
from datetime import datetime
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    MultilineInput,
    IntInput,
    FileInput
)
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.template.field.base import Output


class FlowToolComponent(Component):
    display_name = i18n.t('components.logic.flow_tool.display_name')
    description = i18n.t('components.logic.flow_tool.description')
    documentation: str = "https://docs.langflow.org/components-logic#flow-tool"
    icon = "Workflow"
    name = "FlowTool"

    inputs = [
        MessageTextInput(
            name="flow_id",
            display_name=i18n.t(
                'components.logic.flow_tool.flow_id.display_name'),
            info=i18n.t('components.logic.flow_tool.flow_id.info'),
            required=True,
        ),
        FileInput(
            name="flow_file",
            display_name=i18n.t(
                'components.logic.flow_tool.flow_file.display_name'),
            info=i18n.t('components.logic.flow_tool.flow_file.info'),
            file_types=[".json"],
            advanced=True,
        ),
        MultilineInput(
            name="input_parameters",
            display_name=i18n.t(
                'components.logic.flow_tool.input_parameters.display_name'),
            info=i18n.t('components.logic.flow_tool.input_parameters.info'),
            placeholder='{\n  "param1": "value1",\n  "param2": "value2"\n}',
        ),
        HandleInput(
            name="input_data",
            display_name=i18n.t(
                'components.logic.flow_tool.input_data.display_name'),
            info=i18n.t('components.logic.flow_tool.input_data.info'),
            input_types=["Data", "Message", "Text"],
            required=False,
        ),
        DropdownInput(
            name="execution_mode",
            display_name=i18n.t(
                'components.logic.flow_tool.execution_mode.display_name'),
            info=i18n.t('components.logic.flow_tool.execution_mode.info'),
            options=["sync", "async", "background"],
            value="sync",
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.logic.flow_tool.timeout.display_name'),
            info=i18n.t('components.logic.flow_tool.timeout.info'),
            value=300,
            range_spec=(1, 3600),
            advanced=True,
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.logic.flow_tool.max_retries.display_name'),
            info=i18n.t('components.logic.flow_tool.max_retries.info'),
            value=0,
            range_spec=(0, 10),
            advanced=True,
        ),
        BoolInput(
            name="pass_current_context",
            display_name=i18n.t(
                'components.logic.flow_tool.pass_current_context.display_name'),
            info=i18n.t(
                'components.logic.flow_tool.pass_current_context.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_execution_metadata",
            display_name=i18n.t(
                'components.logic.flow_tool.include_execution_metadata.display_name'),
            info=i18n.t(
                'components.logic.flow_tool.include_execution_metadata.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="output_format",
            display_name=i18n.t(
                'components.logic.flow_tool.output_format.display_name'),
            info=i18n.t('components.logic.flow_tool.output_format.info'),
            options=["auto", "data", "message", "raw"],
            value="auto",
            advanced=True,
        ),
        BoolInput(
            name="cache_results",
            display_name=i18n.t(
                'components.logic.flow_tool.cache_results.display_name'),
            info=i18n.t('components.logic.flow_tool.cache_results.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="error_handling",
            display_name=i18n.t(
                'components.logic.flow_tool.error_handling.display_name'),
            info=i18n.t('components.logic.flow_tool.error_handling.info'),
            options=["raise", "return_error", "return_null"],
            value="raise",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.flow_tool.outputs.result.display_name'),
            name="result",
            method="execute_flow",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.flow_tool.outputs.execution_info.display_name'),
            name="execution_info",
            method="get_execution_info",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.flow_tool.outputs.flow_metadata.display_name'),
            name="flow_metadata",
            method="get_flow_metadata",
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "flow_id":
            # If flow_id is provided, make flow_file optional
            if field_value and field_value.strip():
                build_config["flow_file"]["required"] = False
            else:
                build_config["flow_file"]["required"] = True

        if field_name == "execution_mode":
            if field_value == "async":
                build_config["timeout"]["show"] = True
            elif field_value == "background":
                build_config["timeout"]["show"] = False
                build_config["cache_results"]["show"] = True
            else:  # sync
                build_config["timeout"]["show"] = True
                build_config["cache_results"]["show"] = False

        if field_name == "error_handling":
            if field_value == "return_error":
                build_config["max_retries"]["show"] = False
            else:
                build_config["max_retries"]["show"] = True

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        if not self.flow_id and not self.flow_file:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.missing_flow_identifier')
            self.status = error_message
            raise ValueError(error_message)

        if self.flow_id and self.flow_file:
            warning_message = i18n.t(
                'components.logic.flow_tool.warnings.both_flow_identifiers')
            self.status = warning_message

        if self.input_parameters:
            try:
                json.loads(self.input_parameters)
            except json.JSONDecodeError as e:
                error_message = i18n.t('components.logic.flow_tool.errors.invalid_input_parameters',
                                       error=str(e))
                self.status = error_message
                raise ValueError(error_message) from e

        if self.timeout <= 0:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.invalid_timeout')
            self.status = error_message
            raise ValueError(error_message)

    def _load_flow_definition(self) -> Dict[str, Any]:
        """Load flow definition from ID or file."""
        try:
            if self.flow_file:
                # Load from file
                with open(self.flow_file, 'r', encoding='utf-8') as f:
                    flow_definition = json.load(f)

                success_message = i18n.t('components.logic.flow_tool.success.flow_loaded_from_file',
                                         file=self.flow_file)
                self.status = success_message
                return flow_definition

            elif self.flow_id:
                # Load from flow registry/database
                flow_definition = self._get_flow_by_id(self.flow_id)

                success_message = i18n.t('components.logic.flow_tool.success.flow_loaded_from_id',
                                         flow_id=self.flow_id)
                self.status = success_message
                return flow_definition

            else:
                error_message = i18n.t(
                    'components.logic.flow_tool.errors.no_flow_source')
                raise ValueError(error_message)

        except FileNotFoundError:
            error_message = i18n.t('components.logic.flow_tool.errors.flow_file_not_found',
                                   file=self.flow_file)
            self.status = error_message
            raise ValueError(error_message)
        except json.JSONDecodeError as e:
            error_message = i18n.t('components.logic.flow_tool.errors.invalid_flow_file',
                                   file=self.flow_file, error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
        except Exception as e:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.flow_load_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _get_flow_by_id(self, flow_id: str) -> Dict[str, Any]:
        """Get flow definition by ID (placeholder for actual implementation)."""
        # This would typically interface with a flow registry or database
        # For now, return a mock implementation

        # In a real implementation, this would:
        # 1. Query the flow database/registry
        # 2. Validate permissions
        # 3. Return the flow definition

        raise NotImplementedError(
            i18n.t('components.logic.flow_tool.errors.flow_registry_not_implemented'))

    def _prepare_execution_context(self) -> Dict[str, Any]:
        """Prepare execution context for the flow."""
        context = {}

        # Add input parameters
        if self.input_parameters:
            try:
                params = json.loads(self.input_parameters)
                context.update(params)
            except json.JSONDecodeError:
                pass

        # Add input data
        if self.input_data:
            if isinstance(self.input_data, Data):
                context["input_data"] = self.input_data.data
            elif isinstance(self.input_data, Message):
                context["input_message"] = {
                    "text": self.input_data.text,
                    "sender": getattr(self.input_data, 'sender', None),
                    "session_id": getattr(self.input_data, 'session_id', None),
                }
            else:
                context["input_text"] = str(self.input_data)

        # Add current context if requested
        if self.pass_current_context:
            context["parent_flow"] = {
                "flow_id": getattr(self.graph, 'flow_id', None) if hasattr(self, 'graph') else None,
                "session_id": self._get_current_session_id(),
                "timestamp": datetime.now().isoformat(),
            }

        return context

    def _get_current_session_id(self) -> Optional[str]:
        """Get current session ID."""
        if hasattr(self, 'graph') and self.graph:
            return getattr(self.graph, 'session_id', None)
        return None

    async def _execute_flow_async(self, flow_definition: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute flow asynchronously."""
        # This is a placeholder for actual async flow execution
        # In a real implementation, this would:
        # 1. Create a flow executor instance
        # 2. Set up the execution environment
        # 3. Execute the flow with the given context
        # 4. Return the results

        await asyncio.sleep(0.1)  # Simulate async execution

        return {
            "status": "completed",
            "result": "Mock async execution result",
            "execution_time": 0.1,
            "timestamp": datetime.now().isoformat(),
        }

    def _execute_flow_sync(self, flow_definition: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute flow synchronously."""
        # This is a placeholder for actual sync flow execution
        # In a real implementation, this would:
        # 1. Create a flow executor instance
        # 2. Set up the execution environment
        # 3. Execute the flow with the given context
        # 4. Return the results

        return {
            "status": "completed",
            "result": "Mock sync execution result",
            "execution_time": 0.05,
            "timestamp": datetime.now().isoformat(),
        }

    def _format_output(self, result: Any) -> Any:
        """Format the execution result based on output_format."""
        if self.output_format == "raw":
            return result

        elif self.output_format == "data":
            if isinstance(result, dict):
                return Data(data=result)
            else:
                return Data(data={"result": result})

        elif self.output_format == "message":
            if isinstance(result, dict) and "result" in result:
                text = str(result["result"])
            else:
                text = str(result)
            return Message(text=text)

        else:  # auto
            if isinstance(result, dict):
                return Data(data=result)
            elif isinstance(result, str):
                return Message(text=result)
            else:
                return result

    def execute_flow(self) -> Any:
        """Execute the specified flow and return results."""
        try:
            self._validate_inputs()

            # Load flow definition
            flow_definition = self._load_flow_definition()

            # Prepare execution context
            context = self._prepare_execution_context()

            # Execute flow based on mode
            start_time = datetime.now()

            if self.execution_mode == "async":
                # For async execution in a sync context, we'll run it in an event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    asyncio.wait_for(
                        self._execute_flow_async(flow_definition, context),
                        timeout=self.timeout
                    )
                )

            elif self.execution_mode == "background":
                # For background execution, we'll simulate it
                # In a real implementation, this would queue the job
                result = {
                    "status": "queued",
                    "job_id": f"job_{datetime.now().timestamp()}",
                    "message": "Flow execution queued for background processing",
                    "timestamp": datetime.now().isoformat(),
                }

            else:  # sync
                result = self._execute_flow_sync(flow_definition, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            # Add execution metadata if requested
            if self.include_execution_metadata and isinstance(result, dict):
                result["execution_metadata"] = {
                    "execution_mode": self.execution_mode,
                    "execution_time": execution_time,
                    "flow_id": self.flow_id,
                    "timeout": self.timeout,
                    "retries_used": 0,  # Would track actual retries
                    "timestamp": datetime.now().isoformat(),
                }

            # Format output
            formatted_result = self._format_output(result)

            success_message = i18n.t('components.logic.flow_tool.success.flow_executed',
                                     time=execution_time)
            self.status = success_message

            return formatted_result

        except asyncio.TimeoutError:
            error_message = i18n.t('components.logic.flow_tool.errors.execution_timeout',
                                   timeout=self.timeout)
            self.status = error_message
            if self.error_handling == "raise":
                raise ValueError(error_message)
            elif self.error_handling == "return_error":
                return Data(data={"error": error_message, "type": "timeout"})
            else:  # return_null
                return None

        except Exception as e:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.execution_error', error=str(e))
            self.status = error_message
            if self.error_handling == "raise":
                raise ValueError(error_message) from e
            elif self.error_handling == "return_error":
                return Data(data={"error": str(e), "type": "execution_error"})
            else:  # return_null
                return None

    def get_execution_info(self) -> Data:
        """Get information about the flow execution."""
        try:
            context = self._prepare_execution_context()

            execution_info = {
                "flow_id": self.flow_id,
                "flow_file": self.flow_file,
                "execution_mode": self.execution_mode,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "output_format": self.output_format,
                "error_handling": self.error_handling,
                "cache_results": self.cache_results,
                "pass_current_context": self.pass_current_context,
                "include_execution_metadata": self.include_execution_metadata,
                "context_keys": list(context.keys()),
                "context_size": len(str(context)),
                "timestamp": datetime.now().isoformat(),
            }

            return Data(data=execution_info)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.execution_info_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_flow_metadata(self) -> Data:
        """Get metadata about the target flow."""
        try:
            flow_definition = self._load_flow_definition()

            metadata = {
                "flow_id": self.flow_id,
                "flow_name": flow_definition.get("name", "Unknown"),
                "flow_description": flow_definition.get("description", ""),
                "flow_version": flow_definition.get("version", "1.0"),
                "node_count": len(flow_definition.get("nodes", [])),
                "edge_count": len(flow_definition.get("edges", [])),
                "created_at": flow_definition.get("created_at"),
                "updated_at": flow_definition.get("updated_at"),
                "author": flow_definition.get("author"),
                "tags": flow_definition.get("tags", []),
                "timestamp": datetime.now().isoformat(),
            }

            return Data(data=metadata)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.flow_tool.errors.flow_metadata_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
