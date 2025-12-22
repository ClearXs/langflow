from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid4

import orjson
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from lfx.custom.custom_component.component import Component
from lfx.custom.utils import (
    add_code_field_to_build_config,
    build_custom_component_template,
    get_instance_name,
    update_component_build_config,
)
from lfx.graph.graph.base import Graph
from lfx.graph.schema import RunOutputs
from lfx.log.logger import logger
from lfx.schema.schema import InputValueRequest
from lfx.services.settings.service import SettingsService
from sqlmodel import select

from langflow.api.utils import CurrentActiveUser, DbSession, extract_global_variables_from_headers, parse_value
from langflow.api.v1.schemas import (
    ConfigResponse,
    CustomComponentRequest,
    CustomComponentResponse,
    PreviewUpstreamRequest,
    PreviewUpstreamResponse,
    RunResponse,
    SimplifiedAPIRequest,
    TaskStatusResponse,
    UpdateCustomComponentRequest,
    UploadFileResponse,
)
from langflow.events.event_manager import create_stream_tokens_event_manager
from langflow.exceptions.api import APIException, InvalidChatInputError
from langflow.exceptions.serialization import SerializationError
from langflow.helpers.flow import get_flow_by_id_or_endpoint_name
from langflow.interface.initialize.loading import update_params_with_load_from_db_fields
from langflow.processing.process import process_tweaks, run_graph_internal
from langflow.schema.graph import Tweaks
from langflow.services.auth.utils import api_key_security, get_current_active_user, get_webhook_user
from langflow.services.cache.utils import save_uploaded_file
from langflow.services.database.models.flow.model import Flow, FlowRead
from langflow.services.database.models.flow.utils import get_all_webhook_components_in_flow
from langflow.services.database.models.user.model import User, UserRead
from langflow.services.deps import get_queue_service, get_session_service, get_settings_service, get_telemetry_service
from langflow.services.job_queue.service import JobQueueService
from langflow.services.telemetry.schema import RunPayload
from langflow.utils.compression import compress_response
from langflow.utils.version import get_version_info

if TYPE_CHECKING:
    from langflow.events.event_manager import EventManager

router = APIRouter(tags=["Base"])


def _remove_code_from_graph_data(graph_data: dict) -> dict:
    """Remove code.value from built-in components only in graph_data.

    Rationale:
    - Built-in components: loaded from module, don't need code storage
    - Custom components: code must be preserved for persistence
    - Reduces _graph_data size by ~88% for built-in components

    Args:
        graph_data: Original graph data with code

    Returns:
        Optimized graph data with code removed only from built-in components
    """
    import copy

    if not graph_data or not isinstance(graph_data, dict):
        return graph_data

    optimized = copy.deepcopy(graph_data)

    for node in optimized.get("nodes", []):
        if not isinstance(node, dict):
            continue

        # Navigate to node data and template
        node_data = node.get("data", {}).get("node", {})
        template = node_data.get("template", {})

        # Check if this is a built-in component
        # official=False means custom component, undefined/True means built-in
        is_builtin = node_data.get("official") is not False

        # Only remove code.value for built-in components
        # Custom components (official=False) retain their code
        if is_builtin and "code" in template and isinstance(template["code"], dict):
            if "value" in template["code"]:
                template["code"]["value"] = ""
                # Add marker for debugging
                template["code"]["_removed"] = True

    return optimized


async def parse_input_request_from_body(http_request: Request) -> SimplifiedAPIRequest:
    """Parse SimplifiedAPIRequest from HTTP request body.

    This function handles the case where FastAPI can't automatically parse the request body
    due to the presence of a Request parameter in the endpoint signature.

    Args:
        http_request: The FastAPI Request object

    Returns:
        SimplifiedAPIRequest: Parsed request or default instance if parsing fails
    """
    try:
        body = await http_request.body()
        if body:
            body_data = orjson.loads(body)
            return SimplifiedAPIRequest(**body_data)
        return SimplifiedAPIRequest()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to parse request body: {exc}")
        return SimplifiedAPIRequest()


@router.get("/all", dependencies=[Depends(get_current_active_user)])
async def get_all():
    """Retrieve all component types with compression for better performance.

    Returns a compressed response containing all available component types.
    """
    from langflow.interface.components import get_and_cache_all_types_dict

    try:
        all_types = await get_and_cache_all_types_dict(settings_service=get_settings_service())
        # Return compressed response using our utility function
        return compress_response(all_types)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/force_all", dependencies=[Depends(get_current_active_user)])
async def get_all_force():
    """Retrieve all component types with compression for better performance, forcing a refresh of the cache.

    Returns a compressed response containing all available component types.
    """
    from langflow.interface.components import get_and_cache_all_types_dict

    try:
        all_types = await get_and_cache_all_types_dict(settings_service=get_settings_service(), force_refresh=True)
        # Return compressed response using our utility function
        return compress_response(all_types)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def validate_input_and_tweaks(input_request: SimplifiedAPIRequest) -> None:
    # If the input_value is not None and the input_type is "chat"
    # then we need to check the tweaks if the ChatInput component is present
    # and if its input_value is not None
    # if so, we raise an error
    if not input_request.tweaks:
        return

    for key, value in input_request.tweaks.items():
        if not isinstance(value, dict):
            continue

        input_value = value.get("input_value")
        if input_value is None:
            continue

        request_has_input = input_request.input_value is not None

        if any(chat_key in key for chat_key in ("ChatInput", "Chat Input")):
            if request_has_input and input_request.input_type == "chat":
                msg = "If you pass an input_value to the chat input, you cannot pass a tweak with the same name."
                raise InvalidChatInputError(msg)

        elif (
            any(text_key in key for text_key in ("TextInput", "Text Input"))
            and request_has_input
            and input_request.input_type == "text"
        ):
            msg = "If you pass an input_value to the text input, you cannot pass a tweak with the same name."
            raise InvalidChatInputError(msg)


async def simple_run_flow(
    flow: Flow,
    input_request: SimplifiedAPIRequest,
    *,
    stream: bool = False,
    api_key_user: User | None = None,
    event_manager: EventManager | None = None,
    context: dict | None = None,
    run_id: str | None = None,
):
    validate_input_and_tweaks(input_request)
    try:
        task_result: list[RunOutputs] = []
        user_id = api_key_user.id if api_key_user else None
        flow_id_str = str(flow.id)
        if flow.data is None:
            msg = f"Flow {flow_id_str} has no data"
            raise ValueError(msg)
        graph_data = flow.data.copy()
        graph_data = process_tweaks(graph_data, input_request.tweaks or {}, stream=stream)
        graph = Graph.from_payload(
            graph_data, flow_id=flow_id_str, user_id=str(user_id), flow_name=flow.name, context=context
        )
        if run_id is None:
            run_id = str(uuid4())
        graph.set_run_id(run_id)
        inputs = None
        if input_request.input_value is not None:
            inputs = [
                InputValueRequest(
                    components=[],
                    input_value=input_request.input_value,
                    type=input_request.input_type,
                )
            ]
        if input_request.output_component:
            outputs = [input_request.output_component]
        else:
            outputs = [
                vertex.id
                for vertex in graph.vertices
                if input_request.output_type == "debug"
                or (
                    vertex.is_output
                    # type: ignore[operator]
                    and (input_request.output_type == "any" or input_request.output_type in vertex.id.lower())
                )
            ]
        task_result, session_id = await run_graph_internal(
            graph=graph,
            flow_id=flow_id_str,
            session_id=input_request.session_id,
            inputs=inputs,
            outputs=outputs,
            stream=stream,
            event_manager=event_manager,
        )

        return RunResponse(outputs=task_result, session_id=session_id)

    except sa.exc.StatementError as exc:
        raise ValueError(str(exc)) from exc


async def simple_run_flow_task(
    flow: Flow,
    input_request: SimplifiedAPIRequest,
    *,
    stream: bool = False,
    api_key_user: User | None = None,
    event_manager: EventManager | None = None,
    telemetry_service=None,
    start_time: float | None = None,
    run_id: str | None = None,
):
    """Run a flow task as a BackgroundTask, therefore it should not throw exceptions."""
    try:
        result = await simple_run_flow(
            flow=flow,
            input_request=input_request,
            stream=stream,
            api_key_user=api_key_user,
            event_manager=event_manager,
            run_id=run_id,
        )
        if telemetry_service and start_time is not None:
            await telemetry_service.log_package_run(
                RunPayload(
                    run_is_webhook=True,
                    run_seconds=int(time.perf_counter() - start_time),
                    run_success=True,
                    run_error_message="",
                    run_id=run_id,
                )
            )
        return result  # noqa: TRY300

    except Exception as exc:  # noqa: BLE001
        await logger.aexception(f"Error running flow {flow.id} task")
        if telemetry_service and start_time is not None:
            await telemetry_service.log_package_run(
                RunPayload(
                    run_is_webhook=True,
                    run_seconds=int(time.perf_counter() - start_time),
                    run_success=False,
                    run_error_message=str(exc),
                    run_id=run_id,
                )
            )
        return None


async def consume_and_yield(queue: asyncio.Queue, client_consumed_queue: asyncio.Queue) -> AsyncGenerator:
    """Consumes events from a queue and yields them to the client while tracking timing metrics.

    This coroutine continuously pulls events from the input queue and yields them to the client.
    It tracks timing metrics for how long events spend in the queue and how long the client takes
    to process them.

    Args:
        queue (asyncio.Queue): The queue containing events to be consumed and yielded
        client_consumed_queue (asyncio.Queue): A queue for tracking when the client has consumed events

    Yields:
        The value from each event in the queue

    Notes:
        - Events are tuples of (event_id, value, put_time)
        - Breaks the loop when receiving a None value, signaling completion
        - Tracks and logs timing metrics for queue time and client processing time
        - Notifies client consumption via client_consumed_queue
    """
    while True:
        event_id, value, put_time = await queue.get()
        if value is None:
            break
        get_time = time.time()
        yield value
        get_time_yield = time.time()
        client_consumed_queue.put_nowait(event_id)
        await logger.adebug(
            f"consumed event {event_id} "
            f"(time in queue, {get_time - put_time:.4f}, "
            f"client {get_time_yield - get_time:.4f})"
        )


async def run_flow_generator(
    flow: Flow,
    input_request: SimplifiedAPIRequest,
    api_key_user: User | None,
    event_manager: EventManager,
    client_consumed_queue: asyncio.Queue,
    context: dict | None = None,
) -> None:
    """Executes a flow asynchronously and manages event streaming to the client.

    This coroutine runs a flow with streaming enabled and handles the event lifecycle,
    including success completion and error scenarios.

    Args:
        flow (Flow): The flow to execute
        input_request (SimplifiedAPIRequest): The input parameters for the flow
        api_key_user (User | None): Optional authenticated user running the flow
        event_manager (EventManager): Manages the streaming of events to the client
        client_consumed_queue (asyncio.Queue): Tracks client consumption of events
        context (dict | None): Optional context to pass to the flow

    Events Generated:
        - "add_message": Sent when new messages are added during flow execution
        - "token": Sent for each token generated during streaming
        - "end": Sent when flow execution completes, includes final result
        - "error": Sent if an error occurs during execution

    Notes:
        - Runs the flow with streaming enabled via simple_run_flow()
        - On success, sends the final result via event_manager.on_end()
        - On error, logs the error and sends it via event_manager.on_error()
        - Always sends a final None event to signal completion
    """
    try:
        result = await simple_run_flow(
            flow=flow,
            input_request=input_request,
            stream=True,
            api_key_user=api_key_user,
            event_manager=event_manager,
            context=context,
        )
        event_manager.on_end(data={"result": result.model_dump()})
        await client_consumed_queue.get()
    except (ValueError, InvalidChatInputError, SerializationError) as e:
        await logger.aerror(f"Error running flow: {e}")
        event_manager.on_error(data={"error": str(e)})
    finally:
        await event_manager.queue.put((None, None, time.time))


@router.post("/run/{flow_id_or_name}", response_model=None, response_model_exclude_none=True)
async def simplified_run_flow(
    *,
    background_tasks: BackgroundTasks,
    flow: Annotated[FlowRead | None, Depends(get_flow_by_id_or_endpoint_name)],
    input_request: SimplifiedAPIRequest | None = None,
    stream: bool = False,
    api_key_user: Annotated[UserRead, Depends(api_key_security)],
    context: dict | None = None,
    http_request: Request,
    queue_service: Annotated[JobQueueService, Depends(get_queue_service)],
):
    """Executes a specified flow by ID with support for streaming and telemetry.

    This endpoint executes a flow identified by ID or name, with options for streaming the response
    and tracking execution metrics. It handles both streaming and non-streaming execution modes.

    Args:
        background_tasks (BackgroundTasks): FastAPI background task manager
        flow (FlowRead | None): The flow to execute, loaded via dependency
        input_request (SimplifiedAPIRequest | None): Input parameters for the flow
        stream (bool): Whether to stream the response. When True, enables persistent streaming mode
            where the flow continues running even if the client disconnects, allowing for long-running
            data processing tasks that can be reconnected to later.
        api_key_user (UserRead): Authenticated user from API key
        context (dict | None): Optional context to pass to the flow
        http_request (Request): The incoming HTTP request for extracting global variables

    Returns:
        Union[StreamingResponse, RunResponse]: Either a streaming response for real-time results
        or a RunResponse with the complete execution results

    Raises:
        HTTPException: For flow not found (404) or invalid input (400)
        APIException: For internal execution errors (500)

    Notes:
        - Supports both streaming and non-streaming execution modes
        - Tracks execution time and success/failure via telemetry
        - Handles graceful client disconnection in streaming mode
        - **Persistent Streaming Mode**: When stream=True, the flow continues running even after
          client disconnection, enabling long-running data processing tasks (e.g., Kafka consumers,
          CDC inputs) that can be monitored or controlled via separate API calls
        - Provides detailed error handling with appropriate HTTP status codes
        - Extracts global variables from HTTP headers with prefix X-LANGFLOW-GLOBAL-VAR-*
        - Merges extracted variables with the context parameter as "request_variables"
        - In streaming mode, uses EventManager to handle events:
            - "add_message": New messages during execution
            - "token": Individual tokens during streaming
            - "end": Final execution result
    """
    telemetry_service = get_telemetry_service()

    # If input_request is None, manually parse the request body
    # This happens when FastAPI can't automatically parse it due to the Request parameter
    if input_request is None:
        input_request = await parse_input_request_from_body(http_request)

    if flow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    # Extract request-level variables from headers with prefix X-LANGFLOW-GLOBAL-VAR-*
    request_variables = extract_global_variables_from_headers(http_request.headers)

    # Extract runtime_variables from input_request (highest priority)
    # Note: runtime_variables may already contain auto-wrapped extra fields from the request body
    runtime_variables = None
    if input_request and hasattr(input_request, "runtime_variables") and input_request.runtime_variables:
        runtime_variables = input_request.runtime_variables

        # Handle nested JSON string in 'runtimeVariables' key
        # Client may send: {"runtimeVariables": '{"resultId":123,"folderId":456,...}'}
        if len(runtime_variables) == 1 and "runtimeVariables" in runtime_variables:
            try:
                import json

                nested_json_str = runtime_variables["runtimeVariables"]
                parsed_vars = json.loads(nested_json_str)
                if isinstance(parsed_vars, dict):
                    # Convert all values to strings for consistency
                    runtime_variables = {}
                    for key, value in parsed_vars.items():
                        if value is None:
                            runtime_variables[key] = ""
                        elif isinstance(value, bool):
                            runtime_variables[key] = "true" if value else "false"
                        elif isinstance(value, int | float):
                            runtime_variables[key] = str(value)
                        elif isinstance(value, str):
                            runtime_variables[key] = value
                        else:
                            runtime_variables[key] = json.dumps(value)
                    await logger.adebug(
                        f"Parsed nested JSON from runtimeVariables key: {list(runtime_variables.keys())}"
                    )
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                await logger.awarning(f"Failed to parse nested runtimeVariables JSON: {e}")

        # Enhanced logging for debugging
        variable_count = len(runtime_variables)
        variable_keys = list(runtime_variables.keys())
        await logger.adebug(
            f"Runtime variables in request: {variable_count} variables - Keys: {', '.join(variable_keys)}"
        )

    # Merge runtime variables and request variables with existing context
    if runtime_variables or request_variables:
        if context is None:
            context = {}
        else:
            context = context.copy()  # Don't modify the original context

        # Add runtime_variables (highest priority)
        if runtime_variables:
            context["runtime_variables"] = runtime_variables

            # Detailed logging for debugging variable sources (truncate long values for security)
            truncated_vars = {k: (v[:30] + "..." if len(str(v)) > 30 else v) for k, v in runtime_variables.items()}
            await logger.adebug(f"Context updated with runtime_variables: {truncated_vars}")

        # Add request_variables (from headers, lower priority than runtime_variables)
        if request_variables:
            context["request_variables"] = request_variables
            await logger.adebug(
                f"Context updated with request_variables from headers: {list(request_variables.keys())}"
            )

    start_time = time.perf_counter()

    if stream:
        # Check if this flow is already running (singleton enforcement)
        existing_job_id = queue_service.get_flow_job_id(flow.id)
        if existing_job_id and queue_service.is_job_running(existing_job_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flow {flow.id} is already running with job_id: {existing_job_id}. "
                "Please stop the existing job before starting a new one.",
            )

        # Generate a unique job_id for this streaming job
        job_id = str(uuid4())
        await logger.ainfo(f"[Persistent Stream] Starting flow_id={flow.id}, job_id={job_id}")

        # Create queue and event manager for this job
        asyncio_queue: asyncio.Queue = asyncio.Queue()
        asyncio_queue_client_consumed: asyncio.Queue = asyncio.Queue()
        event_manager = create_stream_tokens_event_manager(queue=asyncio_queue)

        # Create the main task
        main_task = asyncio.create_task(
            run_flow_generator(
                flow=flow,
                input_request=input_request,
                api_key_user=api_key_user,
                event_manager=event_manager,
                client_consumed_queue=asyncio_queue_client_consumed,
                context=context,
            )
        )

        # Register the job in the job queue service with the task
        # This allows the cancel endpoint to find and cancel the task
        queue_service._queues[job_id] = (asyncio_queue, event_manager, main_task, None)

        # Register the flow-job mapping
        queue_service.register_flow_job(flow.id, job_id)
        await logger.ainfo(f"Registered persistent stream: flow_id={flow.id}, job_id={job_id}")

        async def on_disconnect() -> None:
            if stream:
                await logger.adebug(
                    f"Client disconnected but stream=true, keeping task alive for flow {flow.id if flow else 'unknown'}"
                )
                # Persistent streaming mode: do not cancel the task
            else:
                await logger.adebug("Client disconnected, closing tasks")
                main_task.cancel()

        # Return immediately with job_id in response body (not SSE stream)
        # This allows client to disconnect immediately while stream continues
        return {
            "job_id": job_id,
            "flow_id": flow.id,
            "message": "Persistent stream started successfully. Stream will continue running in background.",
        }

    run_id = str(uuid4())
    try:
        result = await simple_run_flow(
            flow=flow,
            input_request=input_request,
            stream=stream,
            api_key_user=api_key_user,
            context=context,
            run_id=run_id,
        )
        end_time = time.perf_counter()
        background_tasks.add_task(
            telemetry_service.log_package_run,
            RunPayload(
                run_is_webhook=False,
                run_seconds=int(end_time - start_time),
                run_success=True,
                run_error_message="",
                run_id=run_id,
            ),
        )

    except ValueError as exc:
        background_tasks.add_task(
            telemetry_service.log_package_run,
            RunPayload(
                run_is_webhook=False,
                run_seconds=int(time.perf_counter() - start_time),
                run_success=False,
                run_error_message=str(exc),
                run_id=run_id,
            ),
        )
        if "badly formed hexadecimal UUID string" in str(exc):
            # This means the Flow ID is not a valid UUID which means it can't find the flow
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if "not found" in str(exc):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise APIException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, exception=exc, flow=flow) from exc
    except InvalidChatInputError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        background_tasks.add_task(
            telemetry_service.log_package_run,
            RunPayload(
                run_is_webhook=False,
                run_seconds=int(time.perf_counter() - start_time),
                run_success=False,
                run_error_message=str(exc),
                run_id=run_id,
            ),
        )
        raise APIException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, exception=exc, flow=flow) from exc

    return result


@router.post("/flows/{flow_id}/nodes/{node_id}/preview_upstream")
async def preview_upstream_data(
    flow_id: str,
    node_id: str,
    request: PreviewUpstreamRequest,
    session: Annotated[DbSession, Depends(get_session_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Preview data from upstream node connected to specified input.

    This endpoint executes the upstream node connected to a specific input of the target node
    and returns field schema information to help with field mapping configuration.

    Args:
        flow_id: Flow identifier
        node_id: Current node identifier (e.g., FieldNameMapping node)
        request: Preview request with input_name and optional sample_size
        session: Database session dependency
        current_user: Authenticated user dependency

    Returns:
        PreviewUpstreamResponse with field schema and sample data

    Raises:
        HTTPException: For flow not found (404) or execution errors (500)
    """
    from langflow.api.v1.preview_utils import analyze_field_structure, execute_upstream_node, find_upstream_node

    try:
        logger.info(f"[PreviewAPI] Previewing upstream data for flow {flow_id}, node {node_id}")

        # 1. Load flow
        stmt = select(Flow).where(Flow.id == UUID(flow_id)).where(Flow.user_id == current_user.id)
        result = await session.exec(stmt)
        flow = result.first()

        if not flow:
            raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")

        flow_data = flow.data

        # 2. Find upstream node
        upstream_node_id = find_upstream_node(flow_data, node_id, request.input_name)
        if not upstream_node_id:
            return PreviewUpstreamResponse(
                success=False,
                fields=[],
                record_count=0,
                error=f"No upstream node connected to input '{request.input_name}'",
            )

        # 3. Execute upstream node
        sample_data = await execute_upstream_node(flow_data, upstream_node_id, sample_size=request.sample_size)

        # 4. Analyze field structure
        fields = analyze_field_structure(sample_data)

        # 5. Return response
        return PreviewUpstreamResponse(
            success=True, fields=fields, record_count=len(sample_data), upstream_node_id=upstream_node_id
        )

    except HTTPException:
        # Re-raise HTTP exceptions as is
        raise
    except Exception as e:
        logger.error(f"[PreviewAPI] Preview upstream failed: {e}", exc_info=True)
        return PreviewUpstreamResponse(success=False, fields=[], record_count=0, error=str(e))


@router.post("/webhook/{flow_id_or_name}", response_model=dict, status_code=HTTPStatus.ACCEPTED)  # noqa: RUF100, FAST003
async def webhook_run_flow(
    flow_id_or_name: str,
    flow: Annotated[Flow, Depends(get_flow_by_id_or_endpoint_name)],
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Run a flow using a webhook request.

    Args:
        flow_id_or_name (str): The flow ID or endpoint name.
        flow (Flow): The flow to be executed.
        request (Request): The incoming HTTP request.
        background_tasks (BackgroundTasks): The background tasks manager.

    Returns:
        dict: A dictionary containing the status of the task.

    Raises:
        HTTPException: If the flow is not found or if there is an error processing the request.
    """
    telemetry_service = get_telemetry_service()
    start_time = time.perf_counter()
    await logger.adebug("Received webhook request")
    error_msg = ""

    # Get the appropriate user for webhook execution based on auth settings
    webhook_user = await get_webhook_user(flow_id_or_name, request)

    try:
        data = await request.body()
    except Exception as exc:
        error_msg = str(exc)
        raise HTTPException(status_code=500, detail=error_msg) from exc

    if not data:
        error_msg = "Request body is empty. You should provide a JSON payload containing the flow ID."
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # get all webhook components in the flow
        webhook_components = get_all_webhook_components_in_flow(flow.data)
        tweaks = {}

        for component in webhook_components:
            tweaks[component["id"]] = {"data": data.decode() if isinstance(data, bytes) else data}
        input_request = SimplifiedAPIRequest(
            input_value="",
            input_type="chat",
            output_type="chat",
            tweaks=tweaks,
            session_id=None,
        )

        await logger.adebug("Starting background task")
        run_id = str(uuid4())
        background_tasks.add_task(
            simple_run_flow_task,
            flow=flow,
            input_request=input_request,
            api_key_user=webhook_user,
            telemetry_service=telemetry_service,
            start_time=start_time,
            run_id=run_id,
        )
    except Exception as exc:
        error_msg = str(exc)
        raise HTTPException(status_code=500, detail=error_msg) from exc

    return {"message": "Task started in the background", "status": "in progress"}


@router.post(
    "/run/advanced/{flow_id}",
    response_model=RunResponse,
    response_model_exclude_none=True,
)
async def experimental_run_flow(
    *,
    session: DbSession,
    flow_id: UUID,
    inputs: list[InputValueRequest] | None = None,
    outputs: list[str] | None = None,
    tweaks: Annotated[Tweaks | None, Body(embed=True)] = None,
    stream: Annotated[bool, Body(embed=True)] = False,
    session_id: Annotated[None | str, Body(embed=True)] = None,
    api_key_user: Annotated[UserRead, Depends(api_key_security)],
) -> RunResponse:
    """Executes a specified flow by ID with optional input values, output selection, tweaks, and streaming capability.

    This endpoint supports running flows with caching to enhance performance and efficiency.

    ### Parameters:
    - `flow_id` (str): The unique identifier of the flow to be executed.
    - `inputs` (List[InputValueRequest], optional): A list of inputs specifying the input values and components
      for the flow. Each input can target specific components and provide custom values.
    - `outputs` (List[str], optional): A list of output names to retrieve from the executed flow.
      If not provided, all outputs are returned.
    - `tweaks` (Optional[Tweaks], optional): A dictionary of tweaks to customize the flow execution.
      The tweaks can be used to modify the flow's parameters and components.
      Tweaks can be overridden by the input values.
    - `stream` (bool, optional): Specifies whether the results should be streamed. Defaults to False.
    - `session_id` (Union[None, str], optional): An optional session ID to utilize existing session data for the flow
      execution.
    - `api_key_user` (User): The user associated with the current API key. Automatically resolved from the API key.

    ### Returns:
    A `RunResponse` object containing the selected outputs (or all if not specified) of the executed flow
    and the session ID.
    The structure of the response accommodates multiple inputs, providing a nested list of outputs for each input.

    ### Raises:
    HTTPException: Indicates issues with finding the specified flow, invalid input formats, or internal errors during
    flow execution.

    ### Example usage:
    ```json
    POST /run/flow_id
    x-api-key: YOUR_API_KEY
    Payload:
    {
        "inputs": [
            {"components": ["component1"], "input_value": "value1"},
            {"components": ["component3"], "input_value": "value2"}
        ],
        "outputs": ["Component Name", "component_id"],
        "tweaks": {"parameter_name": "value", "Component Name": {"parameter_name": "value"}, "component_id": {"parameter_name": "value"}}
        "stream": false
    }
    ```

    This endpoint facilitates complex flow executions with customized inputs, outputs, and configurations,
    catering to diverse application requirements.
    """  # noqa: E501
    session_service = get_session_service()
    flow_id_str = str(flow_id)
    if outputs is None:
        outputs = []
    if inputs is None:
        inputs = [InputValueRequest(components=[], input_value="")]

    if session_id:
        try:
            session_data = await session_service.load_session(session_id, flow_id=flow_id_str)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        graph, _artifacts = session_data or (None, None)
        if graph is None:
            msg = f"Session {session_id} not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    else:
        try:
            # Get the flow that matches the flow_id and belongs to the user
            # flow = session.query(Flow).filter(Flow.id == flow_id).filter(Flow.user_id == api_key_user.id).first()
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == api_key_user.id)
            flow = (await session.exec(stmt)).first()
        except sa.exc.StatementError as exc:
            # StatementError('(builtins.ValueError) badly formed hexadecimal UUID string')
            if "badly formed hexadecimal UUID string" in str(exc):
                await logger.aerror(f"Flow ID {flow_id_str} is not a valid UUID")
                # This means the Flow ID is not a valid UUID which means it can't find the flow
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        if flow is None:
            msg = f"Flow {flow_id_str} not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

        if flow.data is None:
            msg = f"Flow {flow_id_str} has no data"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        try:
            graph_data = flow.data
            graph_data = process_tweaks(graph_data, tweaks or {})
            graph = Graph.from_payload(graph_data, flow_id=flow_id_str)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    try:
        task_result, session_id = await run_graph_internal(
            graph=graph,
            flow_id=flow_id_str,
            session_id=session_id,
            inputs=inputs,
            outputs=outputs,
            stream=stream,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return RunResponse(outputs=task_result, session_id=session_id)


@router.post(
    "/predict/{_flow_id}",
    dependencies=[Depends(api_key_security)],
)
@router.post(
    "/process/{_flow_id}",
    dependencies=[Depends(api_key_security)],
)
async def process(_flow_id) -> None:
    """Endpoint to process an input with a given flow_id."""
    # Raise a depreciation warning
    await logger.awarning(
        "The /process endpoint is deprecated and will be removed in a future version. Please use /run instead."
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="The /process endpoint is deprecated and will be removed in a future version. Please use /run instead.",
    )


@router.get("/task/{_task_id}", deprecated=True)
async def get_task_status(_task_id: str) -> TaskStatusResponse:
    """Get the status of a task by ID (Deprecated).

    This endpoint is deprecated and will be removed in a future version.
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="The /task endpoint is deprecated and will be removed in a future version. Please use /run instead.",
    )


@router.post(
    "/upload/{flow_id}",
    status_code=HTTPStatus.CREATED,
    deprecated=True,
)
async def create_upload_file(
    file: UploadFile,
    flow_id: UUID,
) -> UploadFileResponse:
    """Upload a file for a specific flow (Deprecated).

    This endpoint is deprecated and will be removed in a future version.
    """
    try:
        flow_id_str = str(flow_id)
        file_path = await asyncio.to_thread(save_uploaded_file, file, folder_name=flow_id_str)

        return UploadFileResponse(
            flow_id=flow_id_str,
            file_path=file_path,
        )
    except Exception as exc:
        await logger.aexception("Error saving file")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# get endpoint to return version of langflow
@router.get("/version")
async def get_version():
    return get_version_info()


@router.post("/custom_component", status_code=HTTPStatus.OK)
async def custom_component(
    raw_code: CustomComponentRequest,
    user: CurrentActiveUser,
) -> CustomComponentResponse:
    component = Component(_code=raw_code.code)

    built_frontend_node, component_instance = build_custom_component_template(component, user_id=user.id)
    if raw_code.frontend_node is not None:
        built_frontend_node = await component_instance.update_frontend_node(built_frontend_node, raw_code.frontend_node)

    tool_mode: bool = built_frontend_node.get("tool_mode", False)
    if isinstance(component_instance, Component):
        await component_instance.run_and_validate_update_outputs(
            frontend_node=built_frontend_node,
            field_name="tool_mode",
            field_value=tool_mode,
        )
    type_ = get_instance_name(component_instance)
    return CustomComponentResponse(data=built_frontend_node, type=type_)


@router.post("/custom_component/update", status_code=HTTPStatus.OK)
async def custom_component_update(
    code_request: UpdateCustomComponentRequest,
    user: CurrentActiveUser,
):
    """Update an existing custom component with new code and configuration.

    Processes the provided code and template updates, applies parameter changes (including those loaded from the
    database), updates the component's build configuration, and validates outputs. Returns the updated component node as
    a JSON-serializable dictionary.

    For built-in components (code is empty), loads the component from the module registry.
    For custom components (code is provided), evaluates the code to create the component.

    Raises:
        HTTPException: If an error occurs during component building or updating.
        SerializationError: If serialization of the updated component node fails.
    """
    try:
        # Check if code is empty (built-in component) or provided (custom component)
        if not code_request.code or code_request.code.strip() == "":
            # Built-in component: instantiate directly from module registry
            # Get component type from the request's vertex_type, graph_data, template, or frontend_node
            template = code_request.get_template()

            # Try multiple ways to get the component type (in priority order)
            vertex_type = None

            # Method 0: Check if vertex_type is directly provided (highest priority)
            if code_request.vertex_type:
                vertex_type = code_request.vertex_type

            # Method 1: Check graph_data for node type
            if not vertex_type and code_request.graph_data and code_request.node_id:
                nodes = code_request.graph_data.get("nodes", [])
                for node in nodes:
                    if node.get("id") == code_request.node_id:
                        # Try different locations for type in node data
                        node_data = node.get("data", {})
                        vertex_type = (
                            node_data.get("type")
                            or node_data.get("node", {}).get("type")
                            or node_data.get("node", {}).get("display_name")
                        )
                        break

            # Method 2: Check frontend_node for type
            if not vertex_type and code_request.frontend_node:
                vertex_type = code_request.frontend_node.get("type") or code_request.frontend_node.get("display_name")

            # Method 3: Check template metadata
            if not vertex_type:
                vertex_type = (
                    template.get("_type")
                    or template.get("type")
                    or template.get("display_name")
                    or template.get("_display_name")
                )

            # Method 4: Try to extract from template code field metadata (legacy)
            if not vertex_type and "code" in template:
                code_field = template.get("code", {})
                if isinstance(code_field, dict):
                    vertex_type = code_field.get("_type") or code_field.get("type")

            if not vertex_type:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot determine component type: code is empty and no vertex_type found in request, graph_data, frontend_node, or template",
                )

            # Import and instantiate the built-in component
            from lfx.interface.initialize.loading import _get_component_class_from_registry

            try:
                component_class = _get_component_class_from_registry(vertex_type)
                # Instantiate the component directly
                component = component_class(_parameters={}, _user_id=user.id)
                logger.debug(f"✓ Loaded built-in component '{vertex_type}' from module for update")
            except (ImportError, AttributeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Built-in component '{vertex_type}' not found in registry: {e}",
                ) from e
        else:
            # Custom component: use provided code
            component = Component(_code=code_request.code)

        component_node, cc_instance = build_custom_component_template(
            component,
            user_id=user.id,
        )

        component_node["tool_mode"] = code_request.tool_mode

        if hasattr(cc_instance, "set_attributes"):
            template = code_request.get_template()
            params = {}

            for key, value_dict in template.items():
                if isinstance(value_dict, dict):
                    value = value_dict.get("value")
                    input_type = str(value_dict.get("_input_type"))
                    params[key] = parse_value(value, input_type)

            load_from_db_fields = [
                field_name
                for field_name, field_dict in template.items()
                if isinstance(field_dict, dict) and field_dict.get("load_from_db") and field_dict.get("value")
            ]
            if isinstance(cc_instance, Component):
                params = await update_params_with_load_from_db_fields(cc_instance, params, load_from_db_fields)
                cc_instance.set_attributes(params)
        updated_build_config = code_request.get_template()

        # Add graph_data and node_id to build_config if provided (for preview operations)
        if code_request.graph_data:
            # Remove code from graph_data to reduce size (~88% reduction)
            optimized_graph_data = _remove_code_from_graph_data(code_request.graph_data)
            updated_build_config["_graph_data"] = optimized_graph_data
        if code_request.node_id:
            updated_build_config["_node_id"] = code_request.node_id

        # ==================== 预解析 build_config 中的变量 ====================
        # 创建副本用于变量解析,传给 update_build_config 使用解析后的值
        # 但返回给前端的仍然是原始值,保持用户输入的 {variableName} 模板
        from langflow.schema.dotdict import dotdict

        # 使用 dotdict 构造器创建副本，而不是 deepcopy（避免破坏 dotdict 的方法）
        resolved_build_config = dotdict(
            {k: (dotdict(dict(v)) if isinstance(v, dict) else v) for k, v in updated_build_config.items()}
        )

        if isinstance(cc_instance, Component) and hasattr(cc_instance, "_inputs"):
            for field_name, field_config in resolved_build_config.items():
                # 检查该字段是否在组件的输入定义中
                if field_name in cc_instance._inputs:
                    input_obj = cc_instance._inputs[field_name]

                    # 只处理配置了 resolve_variables=True 的字段
                    if getattr(input_obj, "resolve_variables", False):
                        # 安全地获取值
                        value = field_config.get("value") if isinstance(field_config, dict) else None

                        # 只处理非空字符串
                        if isinstance(value, str) and value:
                            try:
                                # 使用组件实例的同步解析方法（内部会快速检测是否包含变量模式）
                                resolved_value = cc_instance.resolve_variables_in_template_sync(value, field_name)
                                field_config["value"] = resolved_value
                                logger.debug(
                                    f"[API] Pre-resolved variables in field '{field_name}' for component '{cc_instance.display_name}': "
                                    f"'{value}' -> '{resolved_value}'"
                                )
                            except Exception as e:
                                # 解析失败保持原值（已在 resolve_variables_in_template_sync 中处理）
                                logger.warning(f"[API] Failed to pre-resolve variables in field '{field_name}': {e}")

        # 传给 update_build_config 的是解析后的副本
        await update_component_build_config(
            cc_instance,
            build_config=resolved_build_config,  # 使用解析后的副本
            field_value=code_request.field_value,
            field_name=code_request.field,
            action=code_request.action,  # Pass action parameter
        )

        # ==================== 同步组件对 build_config 的修改回原始版本 ====================
        # update_build_config 可能会添加新字段或修改现有字段（如设置下拉选项）
        # 我们需要将这些修改同步回 updated_build_config，但保持 resolve_variables=True 字段的原始值
        if isinstance(cc_instance, Component) and hasattr(cc_instance, "_inputs"):
            for field_name, field_config in resolved_build_config.items():
                # 检查该字段是否在组件的输入定义中
                if field_name in cc_instance._inputs:
                    input_obj = cc_instance._inputs[field_name]
                    # 如果是 resolve_variables=True 的字段，保持原始值不变
                    if getattr(input_obj, "resolve_variables", False):
                        # 同步除了 value 之外的所有修改
                        if isinstance(field_config, dict) and field_name in updated_build_config:
                            original_value = (
                                updated_build_config[field_name].get("value")
                                if isinstance(updated_build_config[field_name], dict)
                                else None
                            )
                            # 复制整个字段配置
                            updated_build_config[field_name] = dotdict(dict(field_config))
                            # 恢复原始值
                            if original_value is not None:
                                updated_build_config[field_name]["value"] = original_value
                        elif field_name not in updated_build_config:
                            # 如果是新添加的字段，直接复制
                            updated_build_config[field_name] = field_config
                    else:
                        # 非 resolve_variables 字段，完全同步
                        updated_build_config[field_name] = field_config
                else:
                    # 不在 _inputs 中的字段（如动态添加的字段），完全同步
                    updated_build_config[field_name] = field_config

        if "code" not in updated_build_config or not updated_build_config.get("code", {}).get("value"):
            # Determine if this is a built-in component: code is empty or only whitespace
            is_builtin = not code_request.code or code_request.code.strip() == ""
            updated_build_config = add_code_field_to_build_config(
                updated_build_config, code_request.code, is_builtin=is_builtin
            )
        component_node["template"] = updated_build_config

        if isinstance(cc_instance, Component):
            await cc_instance.run_and_validate_update_outputs(
                frontend_node=component_node,
                field_name=code_request.field,
                field_value=code_request.field_value,
            )

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return jsonable_encoder(component_node)
    except Exception as exc:
        raise SerializationError.from_exception(exc, data=component_node) from exc


@router.get("/config")
async def get_config() -> ConfigResponse:
    """Retrieve the current application configuration settings.

    Returns:
        ConfigResponse: The configuration settings of the application.

    Raises:
        HTTPException: If an error occurs while retrieving the configuration.
    """
    try:
        settings_service: SettingsService = get_settings_service()
        return ConfigResponse.from_settings(settings_service.settings, settings_service.auth_settings)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/flows/{flow_id}/status")
async def get_flow_streaming_status(
    flow_id: str,
    queue_service: Annotated[JobQueueService, Depends(get_queue_service)],
):
    """Query the streaming status of a persistent flow.

    This endpoint checks if a flow is currently running in persistent streaming mode
    and returns the associated job_id if found.

    Args:
        flow_id (str): The unique identifier for the flow.
        queue_service (JobQueueService): The job queue service dependency.

    Returns:
        dict: A dictionary containing:
            - is_running (bool): Whether the flow is currently running.
            - job_id (str | None): The job ID if running, None otherwise.

    Raises:
        HTTPException: If an error occurs while checking the flow status.
    """
    try:
        await logger.ainfo(f"[Status Query] Checking status for flow_id={flow_id}")

        # Convert string flow_id to UUID for matching with internal mappings
        from uuid import UUID

        try:
            flow_id_uuid = UUID(flow_id)
        except ValueError:
            await logger.aerror(f"[Status Query] Invalid flow_id format: {flow_id}")
            return {"is_running": False, "job_id": None}

        await logger.ainfo(f"[Status Query] Converted flow_id to UUID: {flow_id_uuid}")
        await logger.ainfo(f"[Status Query] Current flow mappings: {queue_service._flow_job_mapping}")
        await logger.ainfo(f"[Status Query] Current queues: {list(queue_service._queues.keys())}")

        job_id = queue_service.get_flow_job_id(flow_id_uuid)
        await logger.ainfo(f"[Status Query] Found job_id: {job_id}")

        if not job_id:
            await logger.ainfo(f"[Status Query] No job_id found for flow {flow_id}")
            return {"is_running": False, "job_id": None}

        is_running = queue_service.is_job_running(job_id)
        await logger.ainfo(f"[Status Query] Job {job_id} running status: {is_running}")

        if not is_running:
            # Job has completed, clean up the mapping
            await logger.ainfo(f"[Status Query] Job {job_id} not running, cleaning up mapping")
            queue_service.cleanup_flow_job(flow_id_uuid)
            return {"is_running": False, "job_id": None}

        await logger.ainfo(f"[Status Query] Flow {flow_id} is running with job {job_id}")
        return {"is_running": True, "job_id": job_id}

    except Exception as exc:
        await logger.aerror(f"Error checking flow status for {flow_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/build/{job_id}/cancel")
async def cancel_build(
    job_id: str,
    queue_service: Annotated[JobQueueService, Depends(get_queue_service)],
):
    """Cancel a running build/streaming job.

    This endpoint stops a persistent streaming job by job_id. It will:
    1. Look up the job in the queue service
    2. Cancel the associated task
    3. Clean up the flow-job mapping

    Args:
        job_id (str): The unique identifier for the job to cancel.
        queue_service (JobQueueService): The job queue service dependency.

    Returns:
        dict: A dictionary containing:
            - message (str): Success message
            - job_id (str): The cancelled job ID

    Raises:
        HTTPException:
            - 404: Job not found or already completed
            - 500: Internal error during cancellation
    """
    try:
        await logger.ainfo(f"[Cancel Request] Attempting to cancel job_id={job_id}")
        await logger.ainfo(f"[Cancel Request] Current queues: {list(queue_service._queues.keys())}")
        await logger.ainfo(f"[Cancel Request] Current flow mappings: {queue_service._flow_job_mapping}")

        # Get the queue entry (queue, event_manager, task, mark_time)
        if job_id not in queue_service._queues:
            await logger.aerror(f"[Cancel Request] Job not found in queue service: {job_id}")
            await logger.aerror(f"[Cancel Request] Available jobs: {list(queue_service._queues.keys())}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}. Available jobs: {list(queue_service._queues.keys())}",
            )

        queue_entry = queue_service._queues[job_id]
        _, _, task, _ = queue_entry

        if task is None:
            await logger.aerror(f"No task found for job_id: {job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job task not found: {job_id}",
            )

        # Check if task is still running
        if task.done():
            await logger.ainfo(f"Job {job_id} already completed")
        else:
            # Cancel the task
            task.cancel()
            await logger.ainfo(f"Cancelled job task: {job_id}")

        # Remove from queue service
        del queue_service._queues[job_id]

        # Find and clean up the flow-job mapping
        for flow_id, mapped_job_id in list(queue_service._flow_job_mapping.items()):
            if mapped_job_id == job_id:
                queue_service.cleanup_flow_job(flow_id)
                await logger.ainfo(f"Cleaned up flow-job mapping: flow_id={flow_id}, job_id={job_id}")
                break

        return {
            "message": "Build cancelled successfully",
            "job_id": job_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        await logger.aerror(f"Error cancelling job {job_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
