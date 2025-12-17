from __future__ import annotations

import ast
import asyncio
import inspect
import threading
from collections.abc import AsyncIterator, Iterator
from copy import deepcopy
from textwrap import dedent
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, get_type_hints
from uuid import UUID

import nanoid
import pandas as pd
import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ValidationError

from lfx.base.tools.constants import (
    TOOL_OUTPUT_DISPLAY_NAME,
    TOOL_OUTPUT_NAME,
    TOOLS_METADATA_INFO,
    TOOLS_METADATA_INPUT_NAME,
)
from lfx.custom.tree_visitor import RequiredInputsVisitor
from lfx.exceptions.component import StreamingError
from lfx.field_typing import Tool  # noqa: TC001

# Lazy import to avoid circular dependency
# from lfx.graph.state.model import create_state_model
# Lazy import to avoid circular dependency
# from lfx.graph.utils import has_chat_output
from lfx.helpers.custom import format_type
from lfx.log.logger import logger
from lfx.memory import astore_message, aupdate_messages, delete_message
from lfx.schema.artifact import get_artifact_type, post_process_raw
from lfx.schema.data import Data
from lfx.schema.log import Log
from lfx.schema.message import ErrorMessage, Message
from lfx.schema.properties import Source
from lfx.template.field.base import UNDEFINED, Input, Output
from lfx.template.frontend_node.custom_components import ComponentFrontendNode
from lfx.utils.async_helpers import run_until_complete
from lfx.utils.util import find_closest_match

from .custom_component import CustomComponent

if TYPE_CHECKING:
    from collections.abc import Callable

    from lfx.base.tools.component_tool import ComponentToolkit
    from lfx.events.event_manager import EventManager
    from lfx.graph.edge.schema import EdgeData
    from lfx.graph.vertex.base import Vertex
    from lfx.inputs.inputs import InputTypes
    from lfx.schema.dataframe import DataFrame
    from lfx.schema.log import LoggableType


_ComponentToolkit = None


def get_component_toolkit():
    global _ComponentToolkit  # noqa: PLW0603
    if _ComponentToolkit is None:
        from lfx.base.tools.component_tool import ComponentToolkit

        _ComponentToolkit = ComponentToolkit
    return _ComponentToolkit


BACKWARDS_COMPATIBLE_ATTRIBUTES = ["user_id", "vertex", "tracing_service"]
CONFIG_ATTRIBUTES = ["_display_name", "_description", "_icon", "_name", "_metadata"]

# ==================== 专用事件循环线程（用于同步上下文中调用异步变量解析） ====================
# 创建独立的事件循环，避免与主事件循环冲突
logger.info("[Component] Creating dedicated event loop for variable resolution...")
_variable_resolution_loop = asyncio.new_event_loop()
_variable_resolution_thread = threading.Thread(
    target=_variable_resolution_loop.run_forever, name="VariableResolutionThread", daemon=True
)
_variable_resolution_thread.start()
# 添加锁用于线程恢复
_thread_recovery_lock = threading.Lock()
logger.info(
    f"[Component] Started dedicated event loop thread for variable resolution: "
    f"thread_name={_variable_resolution_thread.name}, "
    f"thread_alive={_variable_resolution_thread.is_alive()}, "
    f"loop={_variable_resolution_loop}"
)


def _ensure_event_loop_thread_alive():
    """确保事件循环线程是活动的，如果死了就重启它。

    Returns:
        bool: True if thread is alive (or successfully recovered), False otherwise
    """
    global _variable_resolution_loop, _variable_resolution_thread

    if _variable_resolution_thread.is_alive():
        return True

    logger.warning("[Component] Event loop thread is DEAD! Attempting recovery...")

    with _thread_recovery_lock:
        # 双重检查：获取锁后再次确认线程状态
        if _variable_resolution_thread.is_alive():
            return True

        try:
            import time

            # 停止旧的事件循环（如果它还在运行）
            if _variable_resolution_loop.is_running() and not _variable_resolution_loop.is_closed():
                # 在循环中调度停止任务
                _variable_resolution_loop.call_soon_threadsafe(_variable_resolution_loop.stop)
                # 等待循环停止
                time.sleep(0.2)

            # 创建新的事件循环和线程（不关闭旧的，避免 "Cannot close a running event loop" 错误）
            _variable_resolution_loop = asyncio.new_event_loop()
            _variable_resolution_thread = threading.Thread(
                target=_variable_resolution_loop.run_forever,
                name="VariableResolutionThread-Recovered",
                daemon=True,
            )
            _variable_resolution_thread.start()

            # 验证新线程已经启动
            time.sleep(0.1)

            if _variable_resolution_thread.is_alive():
                logger.info(
                    f"[Component] Successfully recovered event loop thread: "
                    f"thread_name={_variable_resolution_thread.name}, "
                    f"thread_alive={_variable_resolution_thread.is_alive()}"
                )
                return True
            logger.error("[Component] Thread recovery failed: new thread did not start properly")
            return False
        except Exception as e:
            logger.error(f"[Component] Failed to recover event loop thread: {e}", exc_info=True)
            return False


class PlaceholderGraph(NamedTuple):
    """A placeholder graph structure for components, providing backwards compatibility.

    and enabling component execution without a full graph object.

    This lightweight structure contains essential information typically found in a complete graph,
    allowing components to function in isolation or in simplified contexts.

    Attributes:
        flow_id (str | None): Unique identifier for the flow, if applicable.
        user_id (str | None): Identifier of the user associated with the flow, if any.
        session_id (str | None): Identifier for the current session, if applicable.
        context (dict): Additional contextual information for the component's execution.
        flow_name (str | None): Name of the flow, if available.
    """

    flow_id: str | None
    user_id: str | None
    session_id: str | None
    context: dict
    flow_name: str | None


class Component(CustomComponent):
    inputs: list[InputTypes] = []
    outputs: list[Output] = []
    selected_output: str | None = None
    code_class_base_inheritance: ClassVar[str] = "Component"
    include_universal_input: ClassVar[bool] = False  # Subclasses can set this to True to opt-in

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Automatically inject universal input for components that opt-in.

        This method is called when a subclass of Component is defined. It automatically
        injects a universal HandleInput that can accept any upstream data type to components
        that explicitly opt-in by setting include_universal_input = True.

        Subclasses must opt-in by setting include_universal_input = True.
        """
        super().__init_subclass__(**kwargs)

        # Check if component opted in to universal input injection
        if not getattr(cls, "include_universal_input", False):
            return

        # Process all components that have an inputs attribute
        if hasattr(cls, "inputs") and isinstance(cls.inputs, list):
            import i18n

            from lfx.inputs.inputs import HandleInput

            # Check if upstream_data already exists
            has_upstream = any(hasattr(inp, "name") and inp.name == "upstream_data" for inp in cls.inputs)

            if not has_upstream:
                # Create a universal input that accepts any upstream type
                universal_input = HandleInput(
                    name="upstream_data",
                    display_name=i18n.t("components.common.upstream_data.display_name"),
                    info=i18n.t("components.common.upstream_data.info"),
                    input_types=[],  # Empty list = accept any type
                    required=False,
                    show=True,
                    advanced=False,
                    accepts_any_type=True,  # Skip type validation for universal input
                )

                # Append to existing inputs (don't replace)
                cls.inputs.append(universal_input)

    def __init__(self, **kwargs) -> None:
        # Initialize instance-specific attributes first
        if overlap := self._there_is_overlap_in_inputs_and_outputs():
            msg = f"Inputs and outputs have overlapping names: {overlap}"
            raise ValueError(msg)
        self._output_logs: dict[str, list[Log]] = {}
        self._current_output: str = ""
        self._metadata: dict = {}
        self._ctx: dict = {}
        self._code: str | None = None
        self._logs: list[Log] = []

        # Initialize component-specific collections
        self._inputs: dict[str, InputTypes] = {}
        self._outputs_map: dict[str, Output] = {}
        self._results: dict[str, Any] = {}
        self._attributes: dict[str, Any] = {}
        self._edges: list[EdgeData] = []
        self._components: list[Component] = []
        self._event_manager: EventManager | None = None
        self._state_model = None

        # Process input kwargs
        inputs = {}
        config = {}
        for key, value in kwargs.items():
            if key.startswith("_"):
                config[key] = value
            elif key in CONFIG_ATTRIBUTES:
                config[key[1:]] = value
            else:
                inputs[key] = value

        self._parameters = inputs or {}
        self.set_attributes(self._parameters)

        # Store original inputs and config for reference
        self.__inputs = inputs
        self.__config = config or {}

        # Add unique ID if not provided
        if "_id" not in self.__config:
            self.__config |= {"_id": f"{self.__class__.__name__}-{nanoid.generate(size=5)}"}

        # Initialize base class
        super().__init__(**self.__config)

        # Post-initialization setup
        if hasattr(self, "_trace_type"):
            self.trace_type = self._trace_type
        if not hasattr(self, "trace_type"):
            self.trace_type = "chain"

        # Setup inputs and outputs
        self._reset_all_output_values()
        if self.inputs is not None:
            self.map_inputs(self.inputs)
        self.map_outputs()

        # Final setup
        self._set_output_types(list(self._outputs_map.values()))
        self.set_class_code()

    @classmethod
    def get_base_inputs(cls):
        if not hasattr(cls, "_base_inputs"):
            return []
        return cls._base_inputs

    @classmethod
    def get_base_outputs(cls):
        if not hasattr(cls, "_base_outputs"):
            return []
        return cls._base_outputs

    def get_results(self) -> dict[str, Any]:
        return self._results

    def get_artifacts(self) -> dict[str, Any]:
        return self._artifacts

    def get_event_manager(self) -> EventManager | None:
        return self._event_manager

    def get_undesrcore_inputs(self) -> dict[str, InputTypes]:
        return self._inputs

    def get_id(self) -> str:
        return self._id

    def set_id(self, id_: str) -> None:
        self._id = id_

    def get_edges(self) -> list[EdgeData]:
        return self._edges

    def get_components(self) -> list[Component]:
        return self._components

    def get_outputs_map(self) -> dict[str, Output]:
        return self._outputs_map

    def get_output_logs(self) -> dict[str, Any]:
        return self._output_logs

    def _build_source(self, id_: str | None, display_name: str | None, source: str | None) -> Source:
        source_dict = {}
        if id_:
            source_dict["id"] = id_
        if display_name:
            source_dict["display_name"] = display_name
        if source:
            # Handle case where source is a ChatOpenAI and other models objects
            if hasattr(source, "model_name"):
                source_dict["source"] = source.model_name
            elif hasattr(source, "model"):
                source_dict["source"] = str(source.model)
            else:
                source_dict["source"] = str(source)
        return Source(**source_dict)

    def get_incoming_edge_by_target_param(self, target_param: str) -> str | None:
        """Get the source vertex ID for an incoming edge that targets a specific parameter.

        This method delegates to the underlying vertex to find an incoming edge that connects
        to the specified target parameter.

        Args:
            target_param (str): The name of the target parameter to find an incoming edge for

        Returns:
            str | None: The ID of the source vertex if an incoming edge is found, None otherwise
        """
        if self._vertex is None:
            msg = "Vertex not found. Please build the graph first."
            raise ValueError(msg)
        return self._vertex.get_incoming_edge_by_target_param(target_param)

    @property
    def enabled_tools(self) -> list[str] | None:
        """Dynamically determine which tools should be enabled.

        This property can be overridden by subclasses to provide custom tool filtering.
        By default, it returns None, which means all tools are enabled.

        Returns:
            list[str] | None: List of tool names or tags to enable, or None to enable all tools.
        """
        # Default implementation returns None (all tools enabled)
        # Subclasses can override this to provide custom filtering
        return None

    def _there_is_overlap_in_inputs_and_outputs(self) -> set[str]:
        """Check the `.name` of inputs and outputs to see if there is overlap.

        Returns:
            set[str]: Set of names that overlap between inputs and outputs.
        """
        # Create sets of input and output names for O(1) lookup
        input_names = {input_.name for input_ in (self.inputs or []) if input_.name is not None}
        output_names = {output.name for output in (self.outputs or [])}

        # Return the intersection of the sets
        return input_names & output_names

    def get_base_args(self):
        """Get the base arguments required for component initialization.

        Returns:
            dict: A dictionary containing the base arguments:
                - _user_id: The ID of the current user
                - _session_id: The ID of the current session
                - _tracing_service: The tracing service instance for logging/monitoring
        """
        return {
            "_user_id": self.user_id,
            "_session_id": self.graph.session_id,
            "_tracing_service": self.tracing_service,
        }

    @property
    def ctx(self):
        if not hasattr(self, "graph") or self.graph is None:
            msg = "Graph not found. Please build the graph first."
            raise ValueError(msg)
        return self.graph.context

    def add_to_ctx(self, key: str, value: Any, *, overwrite: bool = False) -> None:
        """Add a key-value pair to the context.

        Args:
            key (str): The key to add.
            value (Any): The value to associate with the key.
            overwrite (bool, optional): Whether to overwrite the existing value. Defaults to False.

        Raises:
            ValueError: If the graph is not built.
        """
        if not hasattr(self, "graph") or self.graph is None:
            msg = "Graph not found. Please build the graph first."
            raise ValueError(msg)
        if key in self.graph.context and not overwrite:
            msg = f"Key {key} already exists in context. Set overwrite=True to overwrite."
            raise ValueError(msg)
        self.graph.context.update({key: value})

    def update_ctx(self, value_dict: dict[str, Any]) -> None:
        """Update the context with a dictionary of values.

        Args:
            value_dict (dict[str, Any]): The dictionary of values to update.

        Raises:
            ValueError: If the graph is not built.
        """
        if not hasattr(self, "graph") or self.graph is None:
            msg = "Graph not found. Please build the graph first."
            raise ValueError(msg)
        if not isinstance(value_dict, dict):
            msg = "Value dict must be a dictionary"
            raise TypeError(msg)

        self.graph.context.update(value_dict)

    def _pre_run_setup(self):
        pass

    def set_event_manager(self, event_manager: EventManager | None = None) -> None:
        self._event_manager = event_manager

    def _reset_all_output_values(self) -> None:
        if isinstance(self._outputs_map, dict):
            for output in self._outputs_map.values():
                output.value = UNDEFINED

    def _build_state_model(self):
        if self._state_model:
            return self._state_model
        name = self.name or self.__class__.__name__
        model_name = f"{name}StateModel"
        fields = {}
        for output in self._outputs_map.values():
            fields[output.name] = getattr(self, output.method)
        # Lazy import to avoid circular dependency
        from lfx.graph.state.model import create_state_model

        self._state_model = create_state_model(model_name=model_name, **fields)
        return self._state_model

    def get_state_model_instance_getter(self):
        state_model = self._build_state_model()

        def _instance_getter(_):
            return state_model()

        _instance_getter.__annotations__["return"] = state_model
        return _instance_getter

    def __deepcopy__(self, memo: dict) -> Component:
        if id(self) in memo:
            return memo[id(self)]
        kwargs = deepcopy(self.__config, memo)
        kwargs["inputs"] = deepcopy(self.__inputs, memo)
        new_component = type(self)(**kwargs)
        new_component._code = self._code
        new_component._outputs_map = self._outputs_map
        new_component._inputs = self._inputs
        new_component._edges = self._edges
        new_component._components = self._components
        new_component._parameters = self._parameters
        new_component._attributes = self._attributes
        new_component._output_logs = self._output_logs
        new_component._logs = self._logs  # type: ignore[attr-defined]
        memo[id(self)] = new_component
        return new_component

    def set_class_code(self) -> None:
        # Get the source code of the calling class
        if self._code:
            return
        try:
            module = inspect.getmodule(self.__class__)
            if module is None:
                msg = "Could not find module for class"
                raise ValueError(msg)

            class_code = inspect.getsource(module)
            self._code = class_code
        except (OSError, TypeError) as e:
            msg = f"Could not find source code for {self.__class__.__name__}"
            raise ValueError(msg) from e

    def set(self, **kwargs):
        """Connects the component to other components or sets parameters and attributes.

        Args:
            **kwargs: Keyword arguments representing the connections, parameters, and attributes.

        Returns:
            None

        Raises:
            KeyError: If the specified input name does not exist.
        """
        for key, value in kwargs.items():
            self._process_connection_or_parameters(key, value)
        return self

    def list_inputs(self):
        """Returns a list of input names."""
        return [_input.name for _input in (self.inputs or [])]

    def list_outputs(self):
        """Returns a list of output names."""
        return [_output.name for _output in self._outputs_map.values()]

    async def run(self):
        """Executes the component's logic and returns the result.

        Returns:
            The result of executing the component's logic.
        """
        return await self._run()

    def set_vertex(self, vertex: Vertex) -> None:
        """Sets the vertex for the component.

        Args:
            vertex (Vertex): The vertex to set.

        Returns:
            None
        """
        self._vertex = vertex

    def get_input(self, name: str) -> Any:
        """Retrieves the value of the input with the specified name.

        Args:
            name (str): The name of the input.

        Returns:
            Any: The value of the input.

        Raises:
            ValueError: If the input with the specified name is not found.
        """
        if name in self._inputs:
            return self._inputs[name]
        msg = f"Input {name} not found in {self.__class__.__name__}"
        raise ValueError(msg)

    def get_output(self, name: str) -> Any:
        """Retrieves the output with the specified name.

        Args:
            name (str): The name of the output to retrieve.

        Returns:
            Any: The output value.

        Raises:
            ValueError: If the output with the specified name is not found.
        """
        if name in self._outputs_map:
            return self._outputs_map[name]
        msg = f"Output {name} not found in {self.__class__.__name__}"
        raise ValueError(msg)

    def set_on_output(self, name: str, **kwargs) -> None:
        output = self.get_output(name)
        for key, value in kwargs.items():
            if not hasattr(output, key):
                msg = f"Output {name} does not have a method {key}"
                raise ValueError(msg)
            setattr(output, key, value)

    def set_output_value(self, name: str, value: Any) -> None:
        if name in self._outputs_map:
            self._outputs_map[name].value = value
        else:
            msg = f"Output {name} not found in {self.__class__.__name__}"
            raise ValueError(msg)

    def map_outputs(self) -> None:
        """Maps the given list of outputs to the component.

        Args:
            outputs (List[Output]): The list of outputs to be mapped.

        Raises:
            ValueError: If the output name is None.

        Returns:
            None
        """
        # override outputs (generated from the class code) with vertex outputs
        # if they exist (generated from the frontend)
        outputs = []
        if self._vertex and self._vertex.outputs:
            for output in self._vertex.outputs:
                try:
                    output_ = Output(**output)
                    outputs.append(output_)
                except ValidationError as e:
                    msg = f"Invalid output: {e}"
                    raise ValueError(msg) from e
        else:
            outputs = self.outputs
        for output in outputs:
            if output.name is None:
                msg = "Output name cannot be None."
                raise ValueError(msg)
            # Deepcopy is required to avoid modifying the original component;
            # allows each instance of each component to modify its own output
            self._outputs_map[output.name] = deepcopy(output)

    def map_inputs(self, inputs: list[InputTypes]) -> None:
        """Maps the given inputs to the component.

        Args:
            inputs (List[InputTypes]): A list of InputTypes objects representing the inputs.

        Raises:
            ValueError: If the input name is None.

        """
        # Defensive check: if inputs is None, treat as empty list
        if inputs is None:
            return

        for input_ in inputs:
            if input_.name is None:
                msg = self.build_component_error_message("Input name cannot be None")
                raise ValueError(msg)
            try:
                self._inputs[input_.name] = deepcopy(input_)
            except TypeError:
                self._inputs[input_.name] = input_

    def validate(self, params: dict) -> None:
        """Validates the component parameters.

        Args:
            params (dict): A dictionary containing the component parameters.

        Raises:
            ValueError: If the inputs are not valid.
            ValueError: If the outputs are not valid.
        """
        self._validate_inputs(params)
        self._validate_outputs()

    async def run_and_validate_update_outputs(self, frontend_node: dict, field_name: str, field_value: Any):
        frontend_node = self.update_outputs(frontend_node, field_name, field_value)
        if field_name == "tool_mode" or frontend_node.get("tool_mode"):
            is_tool_mode = field_value or frontend_node.get("tool_mode")
            frontend_node["outputs"] = [self._build_tool_output()] if is_tool_mode else frontend_node["outputs"]
            if is_tool_mode:
                frontend_node.setdefault("template", {})
                frontend_node["tool_mode"] = True
                tools_metadata_input = await self._build_tools_metadata_input()
                frontend_node["template"][TOOLS_METADATA_INPUT_NAME] = tools_metadata_input.to_dict()
                self._append_tool_to_outputs_map()
            elif "template" in frontend_node:
                frontend_node["template"].pop(TOOLS_METADATA_INPUT_NAME, None)
        self.tools_metadata = frontend_node.get("template", {}).get(TOOLS_METADATA_INPUT_NAME, {}).get("value")
        return self._validate_frontend_node(frontend_node)

    def _validate_frontend_node(self, frontend_node: dict):
        # Check if all outputs are either Output or a valid Output model
        for index, output in enumerate(frontend_node["outputs"]):
            if isinstance(output, dict):
                try:
                    output_ = Output(**output)
                    self._set_output_return_type(output_)
                    output_dict = output_.model_dump()
                except ValidationError as e:
                    msg = f"Invalid output: {e}"
                    raise ValueError(msg) from e
            elif isinstance(output, Output):
                # we need to serialize it
                self._set_output_return_type(output)
                output_dict = output.model_dump()
            else:
                msg = f"Invalid output type: {type(output)}"
                raise TypeError(msg)
            frontend_node["outputs"][index] = output_dict
        return frontend_node

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:  # noqa: ARG002
        """Default implementation for updating outputs based on field changes.

        Subclasses can override this to modify outputs based on field_name and field_value.
        """
        return frontend_node

    def _set_output_types(self, outputs: list[Output]) -> None:
        for output in outputs:
            self._set_output_return_type(output)

    def _set_output_return_type(self, output: Output) -> None:
        if output.method is None:
            msg = f"Output {output.name} does not have a method"
            raise ValueError(msg)
        return_types = self._get_method_return_type(output.method)
        output.add_types(return_types)

    def _set_output_required_inputs(self) -> None:
        for output in self.outputs:
            if not output.method:
                continue
            method = getattr(self, output.method, None)
            if not method or not callable(method):
                continue
            try:
                source_code = inspect.getsource(method)
                ast_tree = ast.parse(dedent(source_code))
            except Exception:  # noqa: BLE001
                ast_tree = ast.parse(dedent(self._code or ""))

            visitor = RequiredInputsVisitor(self._inputs)
            visitor.visit(ast_tree)
            output.required_inputs = sorted(visitor.required_inputs)

    def get_output_by_method(self, method: Callable):
        # method is a callable and output.method is a string
        # we need to find the output that has the same method
        output = next((output for output in self._outputs_map.values() if output.method == method.__name__), None)
        if output is None:
            method_name = method.__name__ if hasattr(method, "__name__") else str(method)
            msg = f"Output with method {method_name} not found"
            raise ValueError(msg)
        return output

    def _inherits_from_component(self, method: Callable):
        # check if the method is a method from a class that inherits from Component
        # and that it is an output of that class
        return hasattr(method, "__self__") and isinstance(method.__self__, Component)

    def _method_is_valid_output(self, method: Callable):
        # check if the method is a method from a class that inherits from Component
        # and that it is an output of that class
        return (
            hasattr(method, "__self__")
            and isinstance(method.__self__, Component)
            and method.__self__.get_output_by_method(method)
        )

    def _build_error_string_from_matching_pairs(self, matching_pairs: list[tuple[Output, Input]]):
        text = ""
        for output, input_ in matching_pairs:
            text += f"{output.name}[{','.join(output.types)}]->{input_.name}[{','.join(input_.input_types or [])}]\n"
        return text

    def _find_matching_output_method(self, input_name: str, value: Component):
        """Find the output method from the given component and input name.

        Find the output method from the given component (`value`) that matches the specified input (`input_name`)
        in the current component.
        This method searches through all outputs of the provided component to find outputs whose types match
        the input types of the specified input in the current component. If exactly one matching output is found,
        it returns the corresponding method. If multiple matching outputs are found, it raises an error indicating
        ambiguity. If no matching outputs are found, it raises an error indicating that no suitable output was found.

        Args:
            input_name (str): The name of the input in the current component to match.
            value (Component): The component whose outputs are to be considered.

        Returns:
            Callable: The method corresponding to the matching output.

        Raises:
            ValueError: If multiple matching outputs are found, if no matching outputs are found,
                        or if the output method is invalid.
        """
        # Retrieve all outputs from the given component
        outputs = value._outputs_map.values()
        # Prepare to collect matching output-input pairs
        matching_pairs = []
        # Get the input object from the current component
        input_ = self._inputs[input_name]
        # Iterate over outputs to find matches based on types
        matching_pairs = [
            (output, input_)
            for output in outputs
            for output_type in output.types
            # Check if the output type matches the input's accepted types
            if input_.input_types and output_type in input_.input_types
        ]
        # If multiple matches are found, raise an error indicating ambiguity
        if len(matching_pairs) > 1:
            matching_pairs_str = self._build_error_string_from_matching_pairs(matching_pairs)
            msg = self.build_component_error_message(
                f"There are multiple outputs from {value.display_name} that can connect to inputs: {matching_pairs_str}"
            )
            raise ValueError(msg)
        # If no matches are found, raise an error indicating no suitable output
        if not matching_pairs:
            msg = self.build_input_error_message(input_name, f"No matching output from {value.display_name} found")
            raise ValueError(msg)
        # Get the matching output and input pair
        output, input_ = matching_pairs[0]
        # Ensure that the output method is a valid method name (string)
        if not isinstance(output.method, str):
            msg = self.build_component_error_message(
                f"Method {output.method} is not a valid output of {value.display_name}"
            )
            raise TypeError(msg)
        return getattr(value, output.method)

    def _process_connection_or_parameter(self, key, value) -> None:
        # Special handling for Loop components: check if we're setting a loop-enabled output
        if self._is_loop_connection(key, value):
            self._process_loop_connection(key, value)
            return

        input_ = self._get_or_create_input(key)
        # We need to check if callable AND if it is a method from a class that inherits from Component
        if isinstance(value, Component):
            # We need to find the Output that can connect to an input of the current component
            # if there's more than one output that matches, we need to raise an error
            # because we don't know which one to connect to
            value = self._find_matching_output_method(key, value)
        if callable(value) and self._inherits_from_component(value):
            try:
                self._method_is_valid_output(value)
            except ValueError as e:
                msg = f"Method {value.__name__} is not a valid output of {value.__self__.__class__.__name__}"
                raise ValueError(msg) from e
            self._connect_to_component(key, value, input_)
        else:
            self._set_parameter_or_attribute(key, value)

    def _is_loop_connection(self, key: str, value) -> bool:
        """Check if this is a loop feedback connection.

        A loop connection occurs when:
        1. The key matches an output name of this component
        2. That output has allows_loop=True
        3. The value is a callable method from another component
        """
        # Check if key matches a loop-enabled output
        if key not in self._outputs_map:
            return False

        output = self._outputs_map[key]
        if not getattr(output, "allows_loop", False):
            return False

        # Check if value is a callable method from a Component
        return callable(value) and self._inherits_from_component(value)

    def _process_loop_connection(self, key: str, value) -> None:
        """Process a loop feedback connection.

        Creates a special edge that connects the source component's output
        to this Loop component's loop-enabled output (not an input).
        """
        try:
            self._method_is_valid_output(value)
        except ValueError as e:
            msg = f"Method {value.__name__} is not a valid output of {value.__self__.__class__.__name__}"
            raise ValueError(msg) from e

        source_component = value.__self__
        self._components.append(source_component)
        source_output = source_component.get_output_by_method(value)
        target_output = self._outputs_map[key]

        # Create special loop feedback edge
        self._add_loop_edge(source_component, source_output, target_output)

    def _add_loop_edge(self, source_component, source_output, target_output) -> None:
        """Add a special loop feedback edge that targets an output instead of an input."""
        self._edges.append(
            {
                "source": source_component._id,
                "target": self._id,
                "data": {
                    "sourceHandle": {
                        "dataType": source_component.name or source_component.__class__.__name__,
                        "id": source_component._id,
                        "name": source_output.name,
                        "output_types": source_output.types,
                    },
                    "targetHandle": {
                        # Special loop edge structure - targets an output, not an input
                        "dataType": self.name or self.__class__.__name__,
                        "id": self._id,
                        "name": target_output.name,
                        "output_types": target_output.types,
                    },
                },
            }
        )

    def _process_connection_or_parameters(self, key, value) -> None:
        # if value is a list of components, we need to process each component
        # Note this update make sure it is not a list str | int | float | bool | type(None)
        if isinstance(value, list) and not any(
            isinstance(val, str | int | float | bool | type(None) | Message | Data | StructuredTool) for val in value
        ):
            for val in value:
                self._process_connection_or_parameter(key, val)
        else:
            self._process_connection_or_parameter(key, value)

    def _get_or_create_input(self, key):
        try:
            return self._inputs[key]
        except KeyError:
            input_ = self._get_fallback_input(name=key, display_name=key)
            self._inputs[key] = input_
            self.inputs.append(input_)
            return input_

    def _connect_to_component(self, key, value, input_) -> None:
        component = value.__self__
        self._components.append(component)
        output = component.get_output_by_method(value)
        self._add_edge(component, key, output, input_)

    def _add_edge(self, component, key, output, input_) -> None:
        self._edges.append(
            {
                "source": component._id,
                "target": self._id,
                "data": {
                    "sourceHandle": {
                        "dataType": component.name or component.__class__.__name__,
                        "id": component._id,
                        "name": output.name,
                        "output_types": output.types,
                    },
                    "targetHandle": {
                        "fieldName": key,
                        "id": self._id,
                        "inputTypes": input_.input_types,
                        "type": input_.field_type,
                    },
                },
            }
        )

    def _set_parameter_or_attribute(self, key, value) -> None:
        if isinstance(value, Component):
            methods = ", ".join([f"'{output.method}'" for output in value.outputs])
            msg = f"You set {value.display_name} as value for `{key}`. You should pass one of the following: {methods}"
            raise TypeError(msg)
        self.set_input_value(key, value)
        self._parameters[key] = value
        self._attributes[key] = value

    def __call__(self, **kwargs):
        self.set(**kwargs)

        return run_until_complete(self.run())

    async def _run(self):
        # Resolve callable inputs
        for key, _input in self._inputs.items():
            if asyncio.iscoroutinefunction(_input.value):
                self._inputs[key].value = await _input.value()
            elif callable(_input.value):
                self._inputs[key].value = await asyncio.to_thread(_input.value)

        self.set_attributes({})

        return await self.build_results()

    def __getattr__(self, name: str) -> Any:
        if "_attributes" in self.__dict__ and name in self.__dict__["_attributes"]:
            # It is a dict of attributes that are not inputs or outputs all the raw data it should have the loop input.
            return self.__dict__["_attributes"][name]
        if "_inputs" in self.__dict__ and name in self.__dict__["_inputs"]:
            return self.__dict__["_inputs"][name].value
        if "_outputs_map" in self.__dict__ and name in self.__dict__["_outputs_map"]:
            return self.__dict__["_outputs_map"][name]
        if name in BACKWARDS_COMPATIBLE_ATTRIBUTES:
            return self.__dict__[f"_{name}"]
        if name.startswith("_") and name[1:] in BACKWARDS_COMPATIBLE_ATTRIBUTES:
            return self.__dict__[name]
        if name == "graph":
            # If it got up to here it means it was going to raise
            session_id = self._session_id if hasattr(self, "_session_id") else None
            user_id = self._user_id if hasattr(self, "_user_id") else None
            flow_name = self._flow_name if hasattr(self, "_flow_name") else None
            flow_id = self._flow_id if hasattr(self, "_flow_id") else None
            return PlaceholderGraph(
                flow_id=flow_id, user_id=str(user_id), session_id=session_id, context={}, flow_name=flow_name
            )
        msg = f"Attribute {name} not found in {self.__class__.__name__}"
        raise AttributeError(msg)

    def set_input_value(self, name: str, value: Any) -> None:
        if name in self._inputs:
            input_value = self._inputs[name].value
            if isinstance(input_value, Component):
                methods = ", ".join([f"'{output.method}'" for output in input_value.outputs])
                msg = self.build_input_error_message(
                    name,
                    f"You set {input_value.display_name} as value. You should pass one of the following: {methods}",
                )
                raise ValueError(msg)
            if callable(input_value) and hasattr(input_value, "__self__"):
                msg = self.build_input_error_message(
                    name, f"Input is connected to {input_value.__self__.display_name}.{input_value.__name__}"
                )
                raise ValueError(msg)
            try:
                self._inputs[name].value = value
            except Exception as e:
                msg = f"Error setting input value for {name}: {e}"
                raise ValueError(msg) from e
            if hasattr(self._inputs[name], "load_from_db"):
                self._inputs[name].load_from_db = False
        else:
            msg = self.build_component_error_message(f"Input {name} not found")
            raise ValueError(msg)

    def _validate_outputs(self) -> None:
        # Raise Error if some rule isn't met
        if self.selected_output is not None and self.selected_output not in self._outputs_map:
            output_names = ", ".join(list(self._outputs_map.keys()))
            msg = f"selected_output '{self.selected_output}' is not valid. Must be one of: {output_names}"
            raise ValueError(msg)

    def _map_parameters_on_frontend_node(self, frontend_node: ComponentFrontendNode) -> None:
        for name, value in self._parameters.items():
            frontend_node.set_field_value_in_template(name, value)

    def _map_parameters_on_template(self, template: dict) -> None:
        for name, value in self._parameters.items():
            try:
                template[name]["value"] = value
            except KeyError as e:
                close_match = find_closest_match(name, list(template.keys()))
                if close_match:
                    msg = f"Parameter '{name}' not found in {self.__class__.__name__}. Did you mean '{close_match}'?"
                    raise ValueError(msg) from e
                msg = f"Parameter {name} not found in {self.__class__.__name__}. "
                raise ValueError(msg) from e

    def _get_method_return_type(self, method_name: str) -> list[str]:
        method = getattr(self, method_name)
        return_type = get_type_hints(method).get("return")
        if return_type is None:
            return []
        extracted_return_types = self._extract_return_type(return_type)
        return [format_type(extracted_return_type) for extracted_return_type in extracted_return_types]

    def _update_template(self, frontend_node: dict):
        return frontend_node

    def _is_builtin_component(self) -> bool:
        """Check if this component is built-in (from lfx.components).

        Returns:
            True if built-in, False if custom
        """
        module_name = self.__class__.__module__
        return module_name.startswith("lfx.components.")

    def _is_custom_component(self) -> bool:
        """Check if this is a custom (user-defined) component."""
        return not self._is_builtin_component()

    def to_frontend_node(self):
        # ! This part here is clunky but we need it like this for
        # ! backwards compatibility. We can change how prompt component
        # ! works and then update this later
        field_config = self.get_template_config(self)
        frontend_node = ComponentFrontendNode.from_inputs(**field_config)
        # for key in self._inputs:
        #     frontend_node.set_field_load_from_db_in_template(key, value=False)
        self._map_parameters_on_frontend_node(frontend_node)

        frontend_node_dict = frontend_node.to_dict(keep_name=False)
        frontend_node_dict = self._update_template(frontend_node_dict)
        self._map_parameters_on_template(frontend_node_dict["template"])

        frontend_node = ComponentFrontendNode.from_dict(frontend_node_dict)

        # Only add code field for custom components
        # Built-in components will be loaded from module at runtime
        if self._is_custom_component():
            if not self._code:
                self.set_class_code()
            code_field = Input(
                dynamic=True,
                required=True,
                placeholder="",
                multiline=True,
                value=self._code,
                password=False,
                name="code",
                advanced=True,
                field_type="code",
                is_list=False,
            )
            frontend_node.template.add_field(code_field)
            logger.debug(f"Added code field for custom component '{self.display_name}'")
        else:
            logger.debug(f"Skipped code field for built-in component '{self.display_name}'")

        for output in frontend_node.outputs:
            if output.types:
                continue
            return_types = self._get_method_return_type(output.method)
            output.add_types(return_types)

        frontend_node.validate_component()
        frontend_node.set_base_classes_from_outputs()

        # Get the node dictionary and add selected_output if specified
        node_dict = frontend_node.to_dict(keep_name=False)
        if self.selected_output is not None:
            node_dict["selected_output"] = self.selected_output

        # Add component name to template for accurate type identification
        # This helps frontend to send correct vertex_type when code is empty
        if "template" in node_dict:
            node_dict["template"]["_type"] = self.name or self.__class__.__name__

        return {
            "data": {
                "node": node_dict,
                "type": self.name or self.__class__.__name__,
                "id": self._id,
            },
            "id": self._id,
        }

    def _validate_inputs(self, params: dict) -> None:
        # Params keys are the `name` attribute of the Input objects
        """Validates and assigns input values from the provided parameters dictionary.

        For each parameter matching a defined input, sets the input's value and updates the parameter
        dictionary with the validated value.

        Automatically resolves {variableName} patterns in fields configured with resolve_variables=True.
        """
        for key, value in params.copy().items():
            if key not in self._inputs:
                continue
            input_ = self._inputs[key]

            # 自动变量解析：如果字段配置了 resolve_variables 且值是字符串
            if getattr(input_, "resolve_variables", False) and isinstance(value, str) and value:
                # 使用同步包装方法，内部会快速检测是否需要解析
                value = self.resolve_variables_in_template_sync(value, key)

            # BaseInputMixin has a `validate_assignment=True`
            input_.value = value
            params[input_.name] = input_.value

    def set_attributes(self, params: dict) -> None:
        """Sets component attributes from the given parameters, preventing conflicts with reserved attribute names.

        Raises:
            ValueError: If a parameter name matches a reserved attribute not managed in _attributes and its
            value differs from the current attribute value.
        """
        self._validate_inputs(params)
        attributes = {}
        for key, value in params.items():
            if key in self.__dict__ and key not in self._attributes and value != getattr(self, key):
                msg = (
                    f"{self.__class__.__name__} defines an input parameter named '{key}' "
                    f"that is a reserved word and cannot be used."
                )
                raise ValueError(msg)
            attributes[key] = value
        for key, input_obj in self._inputs.items():
            if key not in attributes and key not in self._attributes:
                attributes[key] = input_obj.value or None

        self._attributes.update(attributes)

    def _set_outputs(self, outputs: list[dict]) -> None:
        self.outputs = [Output(**output) for output in outputs]
        for output in self.outputs:
            setattr(self, output.name, output)
            self._outputs_map[output.name] = output

    def get_trace_as_inputs(self):
        predefined_inputs = {
            input_.name: input_.value
            for input_ in (self.inputs or [])
            if hasattr(input_, "trace_as_input") and input_.trace_as_input
        }
        # Runtime inputs
        runtime_inputs = {name: input_.value for name, input_ in self._inputs.items() if hasattr(input_, "value")}
        return {**predefined_inputs, **runtime_inputs}

    def get_trace_as_metadata(self):
        return {
            input_.name: input_.value
            for input_ in (self.inputs or [])
            if hasattr(input_, "trace_as_metadata") and input_.trace_as_metadata
        }

    async def _build_with_tracing(self):
        inputs = self.get_trace_as_inputs()
        metadata = self.get_trace_as_metadata()
        async with self.tracing_service.trace_component(self, self.trace_name, inputs, metadata):
            results, artifacts = await self._build_results()
            self.tracing_service.set_outputs(self.trace_name, results)

        return results, artifacts

    async def _build_without_tracing(self):
        return await self._build_results()

    async def build_results(self):
        """Build the results of the component."""
        if hasattr(self, "graph"):
            session_id = self.graph.session_id
        elif hasattr(self, "_session_id"):
            session_id = self._session_id
        else:
            session_id = None
        try:
            if self.tracing_service:
                return await self._build_with_tracing()
            return await self._build_without_tracing()
        except StreamingError as e:
            await self.send_error(
                exception=e.cause,
                session_id=session_id,
                trace_name=getattr(self, "trace_name", None),
                source=e.source,
            )
            raise e.cause  # noqa: B904
        except Exception as e:
            await self.send_error(
                exception=e,
                session_id=session_id,
                source=Source(id=self._id, display_name=self.display_name, source=self.display_name),
                trace_name=getattr(self, "trace_name", None),
            )
            raise

    async def _build_results(self) -> tuple[dict, dict]:
        results, artifacts = {}, {}

        self._pre_run_setup_if_needed()
        self._handle_tool_mode()

        for output in self._get_outputs_to_process():
            self._current_output = output.name
            result = await self._get_output_result(output)
            results[output.name] = result
            artifacts[output.name] = self._build_artifact(result)
            self._log_output(output)

        self._finalize_results(results, artifacts)
        return results, artifacts

    def _pre_run_setup_if_needed(self):
        if hasattr(self, "_pre_run_setup"):
            self._pre_run_setup()

    def _handle_tool_mode(self):
        if (
            hasattr(self, "outputs") and any(getattr(_input, "tool_mode", False) for _input in (self.inputs or []))
        ) or self.add_tool_output:
            self._append_tool_to_outputs_map()

    def _should_process_output(self, output):
        """Determines whether a given output should be processed based on vertex edge configuration.

        Returns True if the component has no vertex or outgoing edges, or if the output's name is among
        the vertex's source edge names.
        """
        if not self._vertex or not self._vertex.outgoing_edges:
            return True
        return output.name in self._vertex.edges_source_names

    def _get_outputs_to_process(self):
        """Returns a list of outputs to process, ordered according to self.outputs.

        Outputs are included only if they should be processed, as determined by _should_process_output.
        First processes outputs in the order defined by self.outputs, then processes any remaining outputs
        from _outputs_map that weren't in self.outputs.

        Returns:
            list: Outputs to be processed in the defined order.

        Raises:
            ValueError: If an output name in self.outputs is not present in _outputs_map.
        """
        result = []
        processed_names = set()

        # First process outputs in the order defined by self.outputs
        for output in self.outputs:
            output_obj = self._outputs_map.get(output.name, deepcopy(output))
            if self._should_process_output(output_obj):
                result.append(output_obj)
                processed_names.add(output_obj.name)

        # Then process any remaining outputs from _outputs_map
        for name, output_obj in self._outputs_map.items():
            if name not in processed_names and self._should_process_output(output_obj):
                result.append(output_obj)

        return result

    async def _get_output_result(self, output):
        """Computes and returns the result for a given output, applying caching and output options.

        If the output is cached and a value is already defined, returns the cached value. Otherwise,
        invokes the associated output method asynchronously, applies output options, updates the cache,
        and returns the result. Raises a ValueError if the output method is not defined, or a TypeError
        if the method invocation fails.
        """
        if output.cache and output.value != UNDEFINED:
            return output.value

        if output.method is None:
            msg = f'Output "{output.name}" does not have a method defined.'
            raise ValueError(msg)

        method = getattr(self, output.method)
        try:
            result = await method() if inspect.iscoroutinefunction(method) else await asyncio.to_thread(method)
        except TypeError as e:
            msg = f'Error running method "{output.method}": {e}'
            raise TypeError(msg) from e

        # Handle Generator/AsyncGenerator detection
        from collections.abc import AsyncGenerator, Generator

        if isinstance(result, (Generator, AsyncGenerator)):
            # Check if this is a streaming component
            is_streaming = getattr(self, "is_streaming_component", False)

            if is_streaming:
                # Streaming component: return Generator as-is
                # Don't iterate it - let StreamingExecutor handle it
                logger.debug(f"Detected Generator for streaming component {self.__class__.__name__}, returning as-is")
                return result
            # Non-streaming component: iterate and collect to list (backwards compatibility)
            logger.debug(
                f"Detected Generator for non-streaming component {self.__class__.__name__}, collecting to list"
            )
            if isinstance(result, AsyncGenerator):
                result = [item async for item in result]
            else:
                # Execute sync generator in thread pool to avoid blocking
                result = await asyncio.to_thread(list, result)

        if (
            self._vertex is not None
            and isinstance(result, Message)
            and result.flow_id is None
            and self._vertex.graph.flow_id is not None
        ):
            result.set_flow_id(self._vertex.graph.flow_id)
        result = output.apply_options(result)
        output.value = result

        return result

    async def resolve_output(self, output_name: str) -> Any:
        """Resolves and returns the value for a specified output by name.

        If output caching is enabled and a value is already available, returns the cached value;
        otherwise, computes and returns the output result. Raises a KeyError if the output name
        does not exist.
        """
        output = self._outputs_map.get(output_name)
        if output is None:
            msg = (
                f"Sorry, an output named '{output_name}' could not be found. "
                "Please ensure that the output is correctly configured and try again."
            )
            raise KeyError(msg)
        if output.cache and output.value != UNDEFINED:
            return output.value
        return await self._get_output_result(output)

    async def resolve_variables_in_template(self, text: str, field_name: str = "template") -> str:
        """Resolve {variableName} patterns in text with actual variable values.

        This method finds all {variableName} patterns in the text and replaces them
        with the actual values from runtime variables, system variables, or global variables.

        Args:
            text: Text containing {variableName} patterns
            field_name: Name of the field using this template (for logging)

        Returns:
            Text with variables resolved to their actual values

        Example:
            Input:  "select * from {tableName} where id = '{uuid32}'"
            Output: "select * from users where id = 'a1b2c3d4e5f6...'"
        """
        import re

        from langflow.services.deps import session_scope

        # Find all {variableName} patterns
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        matches = re.findall(pattern, text)

        if not matches:
            return text

        # Remove duplicates while preserving order
        unique_vars = []
        seen = set()
        for var in matches:
            if var not in seen:
                unique_vars.append(var)
                seen.add(var)

        # Resolve each variable
        resolved_text = text
        async with session_scope() as session:
            for var_name in unique_vars:
                try:
                    # Try to get the variable value
                    var_value = await self.get_variable(
                        name=var_name, field=field_name, session=session, flow_id=getattr(self, "flow_id", None)
                    )
                    # Replace all occurrences of {variableName} with actual value
                    resolved_text = resolved_text.replace(f"{{{var_name}}}", str(var_value))
                except Exception as e:
                    await logger.awarning(f"[{self.__class__.__name__}] Could not resolve variable '{var_name}': {e}")
                    # Keep the original {variableName} if resolution fails

        return resolved_text

    def _should_resolve_variables(self, value: str) -> bool:
        """Quick check if value contains {variableName} pattern.

        Args:
            value: String value to check

        Returns:
            bool: True if value contains {variableName} pattern, False otherwise
        """
        import re

        return bool(re.search(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", value))

    def resolve_variables_in_template_sync(self, text: str, field_name: str = "template") -> str:
        """Synchronous wrapper for resolve_variables_in_template.

        Uses dedicated event loop thread to run async variable resolution
        from synchronous context, avoiding conflicts with main event loop.

        Args:
            text: Text containing {variableName} patterns
            field_name: Name of the field using this template

        Returns:
            Text with variables resolved to their actual values
        """
        # 快速检测：如果不包含变量模式，直接返回
        if not self._should_resolve_variables(text):
            return text

        # 检查并恢复事件循环线程（如果死了）
        thread_recovered = _ensure_event_loop_thread_alive()
        if not thread_recovered:
            logger.error(
                f"[{self.__class__.__name__}] Event loop thread recovery FAILED! "
                f"Falling back to manual synchronous resolution..."
            )
            # 最后的降级方案: 手动同步解析变量（不使用 async）
            try:
                # 提取所有变量名
                import re
                import uuid
                from datetime import datetime

                from langflow.services.variable.constants import is_system_variable

                variable_names = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", text)

                if not variable_names:
                    return text

                resolved_text = text
                resolved_count = 0

                for var_name in variable_names:
                    try:
                        placeholder = f"{{{var_name}}}"

                        # 只处理系统变量（同步方式无法访问数据库获取全局变量和runtime变量）
                        if is_system_variable(var_name):
                            # 手动生成系统变量的值（复制自 service.py:resolve_system_variable）
                            if var_name == "currentDateTime":
                                value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            elif var_name == "currentDate":
                                value = datetime.now().strftime("%Y-%m-%d")
                            elif var_name == "uniqueId24":
                                try:
                                    from bson import ObjectId

                                    value = str(ObjectId())
                                except ImportError:
                                    value = uuid.uuid4().hex[:24]
                            elif var_name == "uuid32":
                                value = uuid.uuid4().hex
                            elif var_name in [
                                "lastStartTime",
                                "lastEndTime",
                                "lastSuccessStartTime",
                                "lastSuccessEndTime",
                            ]:
                                # 流程历史时间变量需要数据库查询，同步模式无法支持
                                logger.warning(
                                    f"[{self.__class__.__name__}] Variable '{var_name}' requires database access, "
                                    f"cannot resolve in manual synchronous mode, keeping placeholder"
                                )
                                continue
                            else:
                                logger.warning(
                                    f"[{self.__class__.__name__}] Unknown system variable '{var_name}', "
                                    f"keeping placeholder"
                                )
                                continue

                            resolved_text = resolved_text.replace(placeholder, value)
                            resolved_count += 1
                        else:
                            # 非系统变量（全局变量或runtime变量）无法在同步模式下解析
                            logger.warning(
                                f"[{self.__class__.__name__}] Variable '{var_name}' is not a system variable, "
                                f"cannot resolve in synchronous fallback mode"
                            )

                    except Exception as e:
                        logger.error(f"[{self.__class__.__name__}] Failed to resolve variable '{var_name}': {e}")

                return resolved_text

            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Manual synchronous resolution failed: {e}", exc_info=True)
                return text

        # 在专用事件循环中调度协程
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.resolve_variables_in_template(text, field_name), _variable_resolution_loop
            )
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to schedule coroutine: {e}")
            return text

        try:
            # 15秒超时（变量解析通常很快）
            return future.result(timeout=15)
        except TimeoutError:
            logger.error(f"[{self.__class__.__name__}] Variable resolution timeout after 15s")
            future.cancel()
            return text
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Variable resolution failed: {type(e).__name__}: {e}")
            return text

    def _resolve_variable_with_fallback(self, variable_value: str, error_translation_key: str) -> str:
        """Resolve a variable value with manual fallback if automatic resolution failed.

        This method handles the common pattern where a field with resolve_variables=True
        might still contain {variableName} if automatic resolution failed. It provides
        a manual fallback by checking graph context for runtime variables.

        Args:
            variable_value: The value that may contain an unresolved {variableName} pattern
            error_translation_key: Translation key for error message (e.g., "components.input_output.csv_input.errors.variable_not_resolved")

        Returns:
            str: The resolved variable value

        Raises:
            ValueError: If variable cannot be resolved

        Example:
            ```python
            def _get_file_id(self) -> str:
                if hasattr(self, "file_id_variable") and self.file_id_variable:
                    variable_value = self.file_id_variable.strip()
                    if variable_value:
                        return self._resolve_variable_with_fallback(
                            variable_value,
                            "components.input_output.csv_input.errors.variable_not_resolved"
                        )
                # ... rest of logic
            ```
        """
        import i18n

        variable_value = variable_value.strip()
        if not variable_value:
            return variable_value

        # Check if it's a variable pattern {variableName} that wasn't resolved
        if not (variable_value.startswith("{") and variable_value.endswith("}")):
            # Already resolved or is a literal value
            return variable_value

        # Variable resolution should have already happened in _validate_inputs()
        # If we still have {variableName}, it means resolution failed - try manual fallback
        var_name = variable_value[1:-1]  # Extract variable name without {}

        # Try to get runtime variables from graph context (same logic as Component.get_variable())
        resolved_value = None
        if hasattr(self, "graph") and self.graph and hasattr(self.graph, "context"):
            context = self.graph.context

            if context:
                # Check for runtime_variables (highest priority)
                runtime_variables = context.get("runtime_variables")

                if runtime_variables and var_name in runtime_variables:
                    resolved_value = runtime_variables[var_name]

                # Backward compatibility: check for request_variables from HTTP headers
                if not resolved_value:
                    request_variables = context.get("request_variables")

                    if request_variables and var_name in request_variables:
                        resolved_value = request_variables[var_name]

        if resolved_value:
            return str(resolved_value).strip()

        # Variable not found - provide helpful error message
        error_msg = i18n.t(error_translation_key, variable=var_name)
        self.status = error_msg
        raise ValueError(error_msg)

    def _build_artifact(self, result):
        """Builds an artifact dictionary containing a string representation, raw data, and type for a result.

        The artifact includes a human-readable representation, the processed raw result, and its determined type.
        """
        custom_repr = self.custom_repr()
        if custom_repr is None and isinstance(result, dict | Data | str):
            custom_repr = result
        if not isinstance(custom_repr, str):
            custom_repr = str(custom_repr)

        raw = self._process_raw_result(result)
        artifact_type = get_artifact_type(self.status or raw, result)
        raw, artifact_type = post_process_raw(raw, artifact_type)
        return {"repr": custom_repr, "raw": raw, "type": artifact_type}

    def _process_raw_result(self, result):
        return self.extract_data(result)

    def extract_data(self, result):
        """Extract the data from the result. this is where the self.status is set."""
        if isinstance(result, Message):
            self.status = result.get_text()
            return (
                self.status if self.status is not None else "No text available"
            )  # Provide a default message if .text_key is missing
        if hasattr(result, "data"):
            return result.data
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, Data | dict | str):
            return result.data if isinstance(result, Data) else result

        if self.status:
            return self.status
        return result

    def _log_output(self, output):
        self._output_logs[output.name] = self._logs
        self._logs = []
        self._current_output = ""

    def _finalize_results(self, results, artifacts):
        self._artifacts = artifacts
        self._results = results
        if self.tracing_service:
            self.tracing_service.set_outputs(self.trace_name, results)

    def custom_repr(self):
        if self.repr_value == "":
            self.repr_value = self.status
        if isinstance(self.repr_value, dict):
            return yaml.dump(self.repr_value)
        if isinstance(self.repr_value, str):
            return self.repr_value
        if isinstance(self.repr_value, BaseModel) and not isinstance(self.repr_value, Data):
            return str(self.repr_value)
        return self.repr_value

    def build_inputs(self):
        """Builds the inputs for the custom component.

        Returns:
            List[Input]: The list of inputs.
        """
        # This function is similar to build_config, but it will process the inputs
        # and return them as a dict with keys being the Input.name and values being the Input.model_dump()
        # Ensure inputs is always a list, even if template_config returns None
        self.inputs = self.template_config.get("inputs", []) or []
        if not self.inputs:
            return {}
        return {_input.name: _input.model_dump(by_alias=True, exclude_none=True) for _input in self.inputs}

    def _get_field_order(self):
        try:
            inputs = self.template_config["inputs"]
            return [field.name for field in inputs]
        except KeyError:
            return []

    def build(self, **kwargs) -> None:
        self.set_attributes(kwargs)

    def _get_fallback_input(self, **kwargs):
        return Input(**kwargs)

    async def to_toolkit(self) -> list[Tool]:
        """Convert component to a list of tools.

        This is a template method that defines the skeleton of the toolkit creation
        algorithm. Subclasses can override _get_tools() to provide custom tool
        implementations while maintaining the metadata update functionality.

        Returns:
            list[Tool]: A list of tools with updated metadata. Each tool contains:
                - name: The name of the tool
                - description: A description of what the tool does
                - tags: List of tags associated with the tool
        """
        # Get tools from subclass implementation
        # Handle both sync and async _get_tools methods
        if asyncio.iscoroutinefunction(self._get_tools):
            tools = await self._get_tools()
        else:
            tools = self._get_tools()

        if hasattr(self, TOOLS_METADATA_INPUT_NAME):
            tools = self._filter_tools_by_status(tools=tools, metadata=self.tools_metadata)
            return self._update_tools_with_metadata(tools=tools, metadata=self.tools_metadata)

        # If no metadata exists yet, filter based on enabled_tools
        return self._filter_tools_by_status(tools=tools, metadata=None)

    async def _get_tools(self) -> list[Tool]:
        """Get the list of tools for this component.

        This method can be overridden by subclasses to provide custom tool implementations.
        The default implementation uses ComponentToolkit.

        Returns:
            list[Tool]: List of tools provided by this component
        """
        component_toolkit: type[ComponentToolkit] = get_component_toolkit()
        return component_toolkit(component=self).get_tools(callbacks=self.get_langchain_callbacks())

    def _extract_tools_tags(self, tools_metadata: list[dict]) -> list[str]:
        """Extract the first tag from each tool's metadata."""
        return [tool["tags"][0] for tool in tools_metadata if tool["tags"]]

    def _update_tools_with_metadata(self, tools: list[Tool], metadata: DataFrame | None) -> list[Tool]:
        """Update tools with provided metadata."""
        component_toolkit: type[ComponentToolkit] = get_component_toolkit()
        return component_toolkit(component=self, metadata=metadata).update_tools_metadata(tools=tools)

    def check_for_tool_tag_change(self, old_tags: list[str], new_tags: list[str]) -> bool:
        # First check length - if different lengths, they can't be equal
        if len(old_tags) != len(new_tags):
            return True
        # Use set comparison for O(n) average case complexity, earlier the old_tags.sort() != new_tags.sort() was used
        return set(old_tags) != set(new_tags)

    def _filter_tools_by_status(self, tools: list[Tool], metadata: pd.DataFrame | None) -> list[Tool]:
        """Filter tools based on their status in metadata.

        Args:
            tools (list[Tool]): List of tools to filter.
            metadata (list[dict] | None): Tools metadata containing status information.

        Returns:
            list[Tool]: Filtered list of tools.
        """
        # Convert metadata to a list of dicts if it's a DataFrame
        metadata_dict = None  # Initialize as None to avoid lint issues with empty dict
        if isinstance(metadata, pd.DataFrame):
            metadata_dict = metadata.to_dict(orient="records")

        # If metadata is None or empty, use enabled_tools
        if not metadata_dict:
            enabled = self.enabled_tools
            return (
                tools
                if enabled is None
                else [
                    tool for tool in tools if any(enabled_name in [tool.name, *tool.tags] for enabled_name in enabled)
                ]
            )

        # Ensure metadata is a list of dicts
        if not isinstance(metadata_dict, list):
            return tools

        # Create a mapping of tool names to their status
        tool_status = {item["name"]: item.get("status", True) for item in metadata_dict}
        return [tool for tool in tools if tool_status.get(tool.name, True)]

    def _build_tool_data(self, tool: Tool) -> dict:
        if tool.metadata is None:
            tool.metadata = {}
        return {
            "name": tool.name,
            "description": tool.description,
            "tags": tool.tags if hasattr(tool, "tags") and tool.tags else [tool.name],
            "status": True,  # Initialize all tools with status True
            "display_name": tool.metadata.get("display_name", tool.name),
            "display_description": tool.metadata.get("display_description", tool.description),
            "readonly": tool.metadata.get("readonly", False),
            "args": tool.args,
            # "args_schema": tool.args_schema,
        }

    async def _build_tools_metadata_input(self):
        try:
            from lfx.inputs.inputs import ToolsInput
        except ImportError as e:
            msg = "Failed to import ToolsInput from lfx.inputs.inputs"
            raise ImportError(msg) from e
        placeholder = None
        tools = []
        try:
            # Handle both sync and async _get_tools methods
            # TODO: this check can be remomved ince get tools is async
            if asyncio.iscoroutinefunction(self._get_tools):
                tools = await self._get_tools()
            else:
                tools = self._get_tools()

            placeholder = "Loading actions..." if len(tools) == 0 else ""
        except (TimeoutError, asyncio.TimeoutError):
            placeholder = "Timeout loading actions"
        except (ConnectionError, OSError, ValueError):
            placeholder = "Error loading actions"
        # Always use the latest tool data
        tool_data = [self._build_tool_data(tool) for tool in tools]
        # print(tool_data)
        if hasattr(self, TOOLS_METADATA_INPUT_NAME):
            old_tags = self._extract_tools_tags(self.tools_metadata)
            new_tags = self._extract_tools_tags(tool_data)
            if self.check_for_tool_tag_change(old_tags, new_tags):
                # If enabled tools are set, update status based on them
                enabled = self.enabled_tools
                if enabled is not None:
                    for item in tool_data:
                        item["status"] = any(enabled_name in [item["name"], *item["tags"]] for enabled_name in enabled)
                self.tools_metadata = tool_data
            else:
                # Preserve existing status values
                existing_status = {item["name"]: item.get("status", True) for item in self.tools_metadata}
                for item in tool_data:
                    item["status"] = existing_status.get(item["name"], True)
                tool_data = self.tools_metadata
        else:
            # If enabled tools are set, update status based on them
            enabled = self.enabled_tools
            if enabled is not None:
                for item in tool_data:
                    item["status"] = any(enabled_name in [item["name"], *item["tags"]] for enabled_name in enabled)
            self.tools_metadata = tool_data

        return ToolsInput(
            name=TOOLS_METADATA_INPUT_NAME,
            placeholder=placeholder,
            display_name="Actions",
            info=TOOLS_METADATA_INFO,
            value=tool_data,
        )

    def get_project_name(self):
        if hasattr(self, "_tracing_service") and self.tracing_service:
            return self.tracing_service.project_name
        return "Langflow"

    def log(self, message: LoggableType | list[LoggableType], name: str | None = None) -> None:
        """Logs a message.

        Args:
            message (LoggableType | list[LoggableType]): The message to log.
            name (str, optional): The name of the log. Defaults to None.
        """
        if name is None:
            name = f"Log {len(self._logs) + 1}"
        log = Log(message=message, type=get_artifact_type(message), name=name)
        self._logs.append(log)
        if self.tracing_service and self._vertex:
            self.tracing_service.add_log(trace_name=self.trace_name, log=log)
        if self._event_manager is not None and self._current_output:
            data = log.model_dump()
            data["output"] = self._current_output
            data["component_id"] = self._id
            self._event_manager.on_log(data=data)

    def _append_tool_output(self) -> None:
        if next((output for output in self.outputs if output.name == TOOL_OUTPUT_NAME), None) is None:
            self.outputs.append(
                Output(
                    name=TOOL_OUTPUT_NAME,
                    display_name=TOOL_OUTPUT_DISPLAY_NAME,
                    method="to_toolkit",
                    types=["Tool"],
                )
            )

    def is_connected_to_chat_output(self) -> bool:
        # Lazy import to avoid circular dependency
        from lfx.graph.utils import has_chat_output

        return has_chat_output(self.graph.get_vertex_neighbors(self._vertex))

    def _should_skip_message(self, message: Message) -> bool:
        """Check if the message should be skipped based on vertex configuration and message type."""
        return (
            self._vertex is not None
            and not (self._vertex.is_output or self._vertex.is_input)
            and not self.is_connected_to_chat_output()
            and not isinstance(message, ErrorMessage)
        )

    def _ensure_message_required_fields(self, message: Message) -> None:
        """Ensure message has required fields for storage (session_id, sender, sender_name).

        Only sets default values if the fields are not already provided.
        """
        from lfx.utils.constants import MESSAGE_SENDER_AI, MESSAGE_SENDER_NAME_AI

        # Set default session_id from graph if not already set
        if (
            not message.session_id
            and hasattr(self, "graph")
            and hasattr(self.graph, "session_id")
            and self.graph.session_id
        ):
            session_id = (
                UUID(self.graph.session_id) if isinstance(self.graph.session_id, str) else self.graph.session_id
            )
            message.session_id = session_id

        # Set default sender if not set (preserves existing values)
        if not message.sender:
            message.sender = MESSAGE_SENDER_AI

        # Set default sender_name if not set (preserves existing values)
        if not message.sender_name:
            message.sender_name = MESSAGE_SENDER_NAME_AI

    async def send_message(self, message: Message, id_: str | None = None, *, skip_db_update: bool = False):
        """Send a message with optional database update control.

        Args:
            message: The message to send
            id_: Optional message ID
            skip_db_update: If True, only update in-memory and send event, skip DB write.
                           Useful during streaming to avoid excessive DB round-trips.
                           Note: This assumes the message already exists in the database with message.id set.
        """
        if self._should_skip_message(message):
            return message

        if hasattr(message, "flow_id") and isinstance(message.flow_id, str):
            message.flow_id = UUID(message.flow_id)

        # Ensure required fields for message storage are set
        self._ensure_message_required_fields(message)

        # If skip_db_update is True and message already has an ID, skip the DB write
        # This path is used during agent streaming to avoid excessive DB round-trips
        if skip_db_update and message.id:
            # Create a fresh Message instance for consistency with normal flow
            stored_message = await Message.create(**message.model_dump())
            self._stored_message_id = stored_message.id
            # Still send the event to update the client in real-time
            # Note: If this fails, we don't need DB cleanup since we didn't write to DB
            await self._send_message_event(stored_message, id_=id_)
        else:
            # Normal flow: store/update in database
            stored_message = await self._store_message(message)

            self._stored_message_id = stored_message.id
            try:
                complete_message = ""
                if (
                    self._should_stream_message(stored_message, message)
                    and message is not None
                    and isinstance(message.text, AsyncIterator | Iterator)
                ):
                    complete_message = await self._stream_message(message.text, stored_message)
                    stored_message.text = complete_message
                    stored_message = await self._update_stored_message(stored_message)
                else:
                    # Only send message event for non-streaming messages
                    await self._send_message_event(stored_message, id_=id_)
            except Exception:
                # remove the message from the database
                await delete_message(stored_message.id)
                raise
        self.status = stored_message
        return stored_message

    async def _store_message(self, message: Message) -> Message:
        flow_id: str | None = None
        if hasattr(self, "graph"):
            # Convert UUID to str if needed
            flow_id = str(self.graph.flow_id) if self.graph.flow_id else None
        stored_messages = await astore_message(message, flow_id=flow_id)
        if len(stored_messages) != 1:
            msg = "Only one message can be stored at a time."
            raise ValueError(msg)
        stored_message = stored_messages[0]
        return await Message.create(**stored_message.model_dump())

    async def _send_message_event(self, message: Message, id_: str | None = None, category: str | None = None) -> None:
        if hasattr(self, "_event_manager") and self._event_manager:
            data_dict = message.model_dump()["data"] if hasattr(message, "data") else message.model_dump()
            if id_ and not data_dict.get("id"):
                data_dict["id"] = id_
            category = category or data_dict.get("category", None)

            def _send_event():
                match category:
                    case "error":
                        self._event_manager.on_error(data=data_dict)
                    case "remove_message":
                        # Check if id exists in data_dict before accessing it
                        if "id" in data_dict:
                            self._event_manager.on_remove_message(data={"id": data_dict["id"]})
                        else:
                            # If no id, try to get it from the message object or id_ parameter
                            message_id = getattr(message, "id", None) or id_
                            if message_id:
                                self._event_manager.on_remove_message(data={"id": message_id})
                    case _:
                        self._event_manager.on_message(data=data_dict)

            await asyncio.to_thread(_send_event)

    def _should_stream_message(self, stored_message: Message, original_message: Message) -> bool:
        return bool(
            hasattr(self, "_event_manager")
            and self._event_manager
            and stored_message.id
            and not isinstance(original_message.text, str)
        )

    async def _update_stored_message(self, message: Message) -> Message:
        """Update the stored message."""
        if hasattr(self, "_vertex") and self._vertex is not None and hasattr(self._vertex, "graph"):
            flow_id = (
                UUID(self._vertex.graph.flow_id)
                if isinstance(self._vertex.graph.flow_id, str)
                else self._vertex.graph.flow_id
            )

            message.flow_id = flow_id

        message_tables = await aupdate_messages(message)
        if not message_tables:
            msg = "Failed to update message"
            raise ValueError(msg)
        message_table = message_tables[0]
        return await Message.create(**message_table.model_dump())

    async def _stream_message(self, iterator: AsyncIterator | Iterator, message: Message) -> str:
        if not isinstance(iterator, AsyncIterator | Iterator):
            msg = "The message must be an iterator or an async iterator."
            raise TypeError(msg)

        if isinstance(iterator, AsyncIterator):
            return await self._handle_async_iterator(iterator, message.id, message)
        try:
            complete_message = ""
            first_chunk = True
            for chunk in iterator:
                complete_message = await self._process_chunk(
                    chunk.content, complete_message, message.id, message, first_chunk=first_chunk
                )
                first_chunk = False
        except Exception as e:
            raise StreamingError(cause=e, source=message.properties.source) from e
        else:
            return complete_message

    async def _handle_async_iterator(self, iterator: AsyncIterator, message_id: str, message: Message) -> str:
        complete_message = ""
        first_chunk = True
        async for chunk in iterator:
            complete_message = await self._process_chunk(
                chunk.content, complete_message, message_id, message, first_chunk=first_chunk
            )
            first_chunk = False
        return complete_message

    async def _process_chunk(
        self, chunk: str, complete_message: str, message_id: str, message: Message, *, first_chunk: bool = False
    ) -> str:
        complete_message += chunk
        if self._event_manager:
            if first_chunk:
                # Send the initial message only on the first chunk
                msg_copy = message.model_copy()
                msg_copy.text = complete_message
                await self._send_message_event(msg_copy, id_=message_id)
            await asyncio.to_thread(
                self._event_manager.on_token,
                data={
                    "chunk": chunk,
                    "id": str(message_id),
                },
            )
        return complete_message

    async def send_error(
        self,
        exception: Exception,
        session_id: str,
        trace_name: str,
        source: Source,
    ) -> Message | None:
        """Send an error message to the frontend."""
        flow_id = self.graph.flow_id if hasattr(self, "graph") else None
        if not session_id:
            return None
        error_message = ErrorMessage(
            flow_id=flow_id,
            exception=exception,
            session_id=session_id,
            trace_name=trace_name,
            source=source,
        )
        await self.send_message(error_message)
        return error_message

    def _append_tool_to_outputs_map(self):
        self._outputs_map[TOOL_OUTPUT_NAME] = self._build_tool_output()
        # add a new input for the tool schema
        # self.inputs.append(self._build_tool_schema())

    def _build_tool_output(self) -> Output:
        return Output(name=TOOL_OUTPUT_NAME, display_name=TOOL_OUTPUT_DISPLAY_NAME, method="to_toolkit", types=["Tool"])

    def get_input_display_name(self, input_name: str) -> str:
        """Get the display name of an input.

        This is a public utility method that subclasses can use to get user-friendly
        display names for inputs when building error messages or UI elements.

        Usage:
            msg = f"Input {self.get_input_display_name(input_name)} not found"

        Args:
            input_name (str): The name of the input.

        Returns:
            str: The display name of the input, or the input name if not found.
        """
        if input_name in self._inputs:
            return getattr(self._inputs[input_name], "display_name", input_name)
        return input_name

    def get_output_display_name(self, output_name: str) -> str:
        """Get the display name of an output.

        This is a public utility method that subclasses can use to get user-friendly
        display names for outputs when building error messages or UI elements.

        Args:
            output_name (str): The name of the output.

        Returns:
            str: The display name of the output, or the output name if not found.
        """
        if output_name in self._outputs_map:
            return getattr(self._outputs_map[output_name], "display_name", output_name)
        return output_name

    def build_input_error_message(self, input_name: str, message: str) -> str:
        """Build an error message for an input.

        This is a public utility method that subclasses can use to create consistent,
        user-friendly error messages that reference inputs by their display names.
        The input name is placed at the beginning to ensure it's visible even if the message is truncated.

        Args:
            input_name (str): The name of the input.
            message (str): The error message.

        Returns:
            str: The formatted error message with display name.
        """
        display_name = self.get_input_display_name(input_name)
        return f"[Input: {display_name}] {message}"

    def build_output_error_message(self, output_name: str, message: str) -> str:
        """Build an error message for an output.

        This is a public utility method that subclasses can use to create consistent,
        user-friendly error messages that reference outputs by their display names.
        The output name is placed at the beginning to ensure it's visible even if the message is truncated.

        Args:
            output_name (str): The name of the output.
            message (str): The error message.

        Returns:
            str: The formatted error message with display name.
        """
        display_name = self.get_output_display_name(output_name)
        return f"[Output: {display_name}] {message}"

    def build_component_error_message(self, message: str) -> str:
        """Build an error message for the component.

        This is a public utility method that subclasses can use to create consistent,
        user-friendly error messages that reference the component by its display name.
        The component name is placed at the beginning to ensure it's visible even if the message is truncated.

        Args:
            message (str): The error message.

        Returns:
            str: The formatted error message with component display name.
        """
        return f"[Component: {self.display_name or self.__class__.__name__}] {message}"

    async def get_upstream_data(
        self, input_name: str, graph_data: dict, sample_size: int | None = None, vertex_id: str | None = None
    ) -> list[Data]:
        """Get data from upstream node connected to specified input.

        This is a utility method for components to fetch actual runtime data from upstream
        nodes during update_build_config. Useful for auto-populating configuration based
        on upstream data structure.

        Args:
            input_name: Name of the input field to get upstream data from
            graph_data: Flow graph data (from build_config or frontend_node)
            sample_size: Optional limit on number of records to return
            vertex_id: Optional vertex ID (auto-detected if not provided)

        Returns:
            List of Data objects from the upstream node's execution

        Raises:
            ValueError: If no upstream node found or execution fails

        Example:
            async def update_build_config(self, build_config, field_value, field_name, action):
                if action == "analyze_fields":
                    # Get graph data from build_config
                    graph_data = build_config.get("_graph_data", {})

                    # Fetch upstream data
                    upstream_data = await self.get_upstream_data(
                        input_name="data_input",
                        graph_data=graph_data,
                        sample_size=10
                    )

                    # Process data for this component's needs
                    fields = self._extract_fields(upstream_data)
                    build_config["my_table"]["value"] = fields

                return build_config
        """
        from lfx.custom.graph_utils import execute_node_and_get_result, find_upstream_node_id

        # Find the vertex ID
        if not vertex_id:
            # Try to get from self._vertex first (runtime context)
            if hasattr(self, "_vertex") and self._vertex:
                vertex_id = self._vertex.id

        if not vertex_id:
            msg = "Component vertex ID not found. Please ensure node_id is passed in design-time context."
            raise ValueError(msg)

        upstream_node_id = find_upstream_node_id(graph_data, vertex_id, input_name)
        if not upstream_node_id:
            msg = f"No upstream node connected to input '{input_name}'"
            raise ValueError(msg)

        # Check if we have a real graph instance (not PlaceholderGraph)
        from lfx.custom.custom_component.component import PlaceholderGraph

        has_real_graph = (
            hasattr(self, "graph")
            and self.graph is not None
            and not isinstance(self.graph, PlaceholderGraph)
            and hasattr(self.graph, "get_vertex")  # Ensure it has the required method
        )

        if has_real_graph:
            # Runtime context - use existing graph
            logger.debug("[Component] Using existing graph instance")
            return await execute_node_and_get_result(self.graph, upstream_node_id, sample_size)

        # Design-time context - need to build a temporary graph
        from lfx.graph.graph.base import Graph

        logger.debug("[Component] Building temporary graph from graph_data (design-time context)")
        logger.debug(f"[Component] graph_data keys: {list(graph_data.keys())}")
        logger.debug(f"[Component] Number of nodes: {len(graph_data.get('nodes', []))}")
        logger.debug(f"[Component] Number of edges: {len(graph_data.get('edges', []))}")

        # Build a temporary graph from graph_data
        try:
            # Graph.from_payload expects edges to have a specific format with nested 'data' field
            # But frontend sends edges without this structure, so we need to transform them
            logger.debug("[Component] Creating Graph.from_payload...")

            # Transform graph_data to match Graph's expected format
            transformed_graph_data = self._transform_graph_data_for_execution(graph_data)

            temp_graph = Graph.from_payload(transformed_graph_data)
            logger.debug("[Component] Temporary graph created successfully")
            logger.debug(
                f"[Component] Temporary graph has {len(temp_graph.vertices) if hasattr(temp_graph, 'vertices') else 0} vertices"
            )

            return await execute_node_and_get_result(temp_graph, upstream_node_id, sample_size)
        except Exception as e:
            logger.exception("[Component] Failed to build or execute temporary graph")
            logger.error(f"[Component] Exception type: {type(e).__name__}")
            logger.error(f"[Component] Exception message: {e!s}")
            msg = f"Failed to build temporary graph for execution: {e}"
            raise ValueError(msg) from e

    def _transform_graph_data_for_execution(self, graph_data: dict) -> dict:
        """Transform frontend graph_data to the format expected by Graph.from_payload.

        Frontend sends edges in React Flow format without nested 'data' field.
        Graph expects edges with data.sourceHandle and data.targetHandle.

        Args:
            graph_data: Graph data from frontend

        Returns:
            Transformed graph data ready for Graph.from_payload
        """
        import json

        transformed_edges = []
        for edge in graph_data.get("edges", []):
            # If edge already has the correct format, use it as-is
            if "data" in edge and isinstance(edge["data"], dict):
                if "sourceHandle" in edge["data"] and "targetHandle" in edge["data"]:
                    transformed_edges.append(edge)
                    continue

            # Transform edge to expected format
            transformed_edge = {"source": edge.get("source"), "target": edge.get("target"), "data": {}}

            # Parse sourceHandle (might be JSON string or dict)
            source_handle = edge.get("sourceHandle", "")
            if isinstance(source_handle, str) and source_handle.startswith("{"):
                try:
                    cleaned = source_handle.replace("œ", '"')
                    source_handle_data = json.loads(cleaned)
                except Exception:
                    source_handle_data = {}
            elif isinstance(source_handle, dict):
                source_handle_data = source_handle
            else:
                source_handle_data = {}

            # Parse targetHandle (might be JSON string or dict)
            target_handle = edge.get("targetHandle", "")
            if isinstance(target_handle, str) and target_handle.startswith("{"):
                try:
                    cleaned = target_handle.replace("œ", '"')
                    target_handle_data = json.loads(cleaned)
                except Exception:
                    target_handle_data = {}
            elif isinstance(target_handle, dict):
                target_handle_data = target_handle
            else:
                target_handle_data = {}

            transformed_edge["data"]["sourceHandle"] = source_handle_data
            transformed_edge["data"]["targetHandle"] = target_handle_data

            # Copy other edge properties
            for key in edge:
                if key not in ["source", "target", "sourceHandle", "targetHandle", "data"]:
                    transformed_edge[key] = edge[key]

            transformed_edges.append(transformed_edge)

        return {"nodes": graph_data.get("nodes", []), "edges": transformed_edges}


def _get_component_toolkit():
    from lfx.base.tools.component_tool import ComponentToolkit

    return ComponentToolkit
