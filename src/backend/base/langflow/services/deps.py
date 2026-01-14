from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from lfx.log.logger import logger

from langflow.services.nacos.service import NacosService
from langflow.services.schema import ServiceType

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lfx.services.settings.service import SettingsService
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.cache.service import AsyncBaseCacheService, CacheService
    from langflow.services.chat.service import ChatService
    from langflow.services.database.service import DatabaseService
    from langflow.services.job_queue.service import JobQueueService
    from langflow.services.session.service import SessionService
    from langflow.services.state.service import StateService
    from langflow.services.storage.service import StorageService
    from langflow.services.store.service import StoreService
    from langflow.services.task.service import TaskService
    from langflow.services.telemetry.service import TelemetryService
    from langflow.services.tracing.service import TracingService
    from langflow.services.variable.service import VariableService


def get_service(service_type: ServiceType, default=None):
    """Retrieves the service instance for the given service type.

    Args:
        service_type (ServiceType): The type of service to retrieve.
        default (ServiceFactory, optional): The default ServiceFactory to use if the service is not found.
            Defaults to None.

    Returns:
        Any: The service instance.

    """
    from lfx.services.manager import get_service_manager

    service_manager = get_service_manager()

    if not service_manager.are_factories_registered():
        # ! This is a workaround to ensure that the service manager is initialized
        # ! Not optimal, but it works for now
        from langflow.services.manager import ServiceManager

        service_manager.register_factories(ServiceManager.get_factories())
    return service_manager.get(service_type, default)


def get_telemetry_service() -> TelemetryService:
    """Retrieves the TelemetryService instance from the service manager.

    Returns:
        TelemetryService: The TelemetryService instance.
    """
    from langflow.services.telemetry.factory import TelemetryServiceFactory

    return get_service(ServiceType.TELEMETRY_SERVICE, TelemetryServiceFactory())


def get_tracing_service() -> TracingService:
    """Retrieves the TracingService instance from the service manager.

    Returns:
        TracingService: The TracingService instance.
    """
    from langflow.services.tracing.factory import TracingServiceFactory

    return get_service(ServiceType.TRACING_SERVICE, TracingServiceFactory())


def get_state_service() -> StateService:
    """Retrieves the StateService instance from the service manager.

    Returns:
        The StateService instance.
    """
    from langflow.services.state.factory import StateServiceFactory

    return get_service(ServiceType.STATE_SERVICE, StateServiceFactory())


def get_storage_service() -> StorageService:
    """Retrieves the storage service instance.

    Returns:
        The storage service instance.
    """
    from langflow.services.storage.factory import StorageServiceFactory

    return get_service(ServiceType.STORAGE_SERVICE, default=StorageServiceFactory())


def get_variable_service() -> VariableService:
    """Retrieves the VariableService instance from the service manager.

    Returns:
        The VariableService instance.

    """
    from langflow.services.variable.factory import VariableServiceFactory

    return get_service(ServiceType.VARIABLE_SERVICE, VariableServiceFactory())


def get_settings_service() -> SettingsService:
    """Retrieves the SettingsService instance.

    If the service is not yet initialized, it will be initialized before returning.

    Returns:
        The SettingsService instance.

    Raises:
        ValueError: If the service cannot be retrieved or initialized.
    """
    from lfx.services.settings.factory import SettingsServiceFactory

    return get_service(ServiceType.SETTINGS_SERVICE, SettingsServiceFactory())


def get_db_service() -> DatabaseService:
    """Retrieves the DatabaseService instance from the service manager.

    Returns:
        The DatabaseService instance.

    """
    from langflow.services.database.factory import DatabaseServiceFactory

    return get_service(ServiceType.DATABASE_SERVICE, DatabaseServiceFactory())


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Retrieves an async session from the database service.

    Yields:
        AsyncSession: An async session object.

    """
    async with session_scope() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for managing an async session scope.

    This context manager is used to manage an async session scope for database operations.
    It ensures that the session is properly committed if no exceptions occur,
    and rolled back if an exception is raised.

    Yields:
        AsyncSession: The async session object.

    Raises:
        Exception: If an error occurs during the session scope.

    """
    db_service = get_db_service()
    async with db_service.with_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await logger.aexception("An error occurred during the session scope.", exception=e)
            await session.rollback()
            raise


def get_cache_service() -> CacheService | AsyncBaseCacheService:
    """Retrieves the cache service from the service manager.

    Returns:
        The cache service instance.
    """
    from langflow.services.cache.factory import CacheServiceFactory

    return get_service(ServiceType.CACHE_SERVICE, CacheServiceFactory())


def get_shared_component_cache_service() -> CacheService:
    """Retrieves the cache service from the service manager.

    Returns:
        The cache service instance.
    """
    from langflow.services.shared_component_cache.factory import SharedComponentCacheServiceFactory

    return get_service(ServiceType.SHARED_COMPONENT_CACHE_SERVICE, SharedComponentCacheServiceFactory())


def get_session_service() -> SessionService:
    """Retrieves the session service from the service manager.

    Returns:
        The session service instance.
    """
    from langflow.services.session.factory import SessionServiceFactory

    return get_service(ServiceType.SESSION_SERVICE, SessionServiceFactory())


def get_task_service() -> TaskService:
    """Retrieves the TaskService instance from the service manager.

    Returns:
        The TaskService instance.

    """
    from langflow.services.task.factory import TaskServiceFactory

    return get_service(ServiceType.TASK_SERVICE, TaskServiceFactory())


def get_chat_service() -> ChatService:
    """Get the chat service instance.

    Returns:
        ChatService: The chat service instance.
    """
    return get_service(ServiceType.CHAT_SERVICE)


def get_store_service() -> StoreService:
    """Retrieves the StoreService instance from the service manager.

    Returns:
        StoreService: The StoreService instance.
    """
    return get_service(ServiceType.STORE_SERVICE)


def get_queue_service() -> JobQueueService:
    """Retrieves the QueueService instance from the service manager."""
    from langflow.services.job_queue.factory import JobQueueServiceFactory

    return get_service(ServiceType.JOB_QUEUE_SERVICE, JobQueueServiceFactory())


def get_nacos_service() -> NacosService:
    """Retrieves the NacosService instance from the service manager."""
    from langflow.services.nacos.factory import NacosServiceFactory

    return get_service(ServiceType.NACOS_SERVICE, NacosServiceFactory())


# ==================== Holo Knowledge System Services ====================


def get_llm_service():
    """Retrieves the LLMService instance from the service manager.

    Returns:
        LLMService: The LLMService instance for managing LLM configurations.
    """
    from langflow.services.llm.factory import LLMServiceFactory

    return get_service(ServiceType.LLM_SERVICE, LLMServiceFactory())


def get_task_logging_service():
    """Retrieves the TaskLoggingService instance from the service manager.

    Returns:
        TaskLoggingService: The TaskLoggingService instance for task logging.
    """
    from langflow.services.task_logging.factory import TaskLoggingServiceFactory

    return get_service(ServiceType.TASK_LOGGING_SERVICE, TaskLoggingServiceFactory())


def get_query_service():
    """Retrieves the QueryService instance from the service manager.

    Returns:
        QueryService: The QueryService instance for query reformulation.
    """
    from langflow.services.query.factory import QueryServiceFactory

    return get_service(ServiceType.QUERY_SERVICE, QueryServiceFactory())


def get_reranker_service():
    """Retrieves the RerankerService instance from the service manager.

    Returns:
        RerankerService: The RerankerService instance for result reranking.
    """
    from langflow.services.reranker.factory import RerankerServiceFactory

    return get_service(ServiceType.RERANKER_SERVICE, RerankerServiceFactory())


def get_celery_app():
    """Retrieves the Celery app instance.

    Returns:
        Celery: The Celery application instance for background task processing.
    """
    from langflow.core.celery_app import celery_app

    return celery_app


def get_connector_service():
    """Retrieves the ConnectorService instance from the service manager.

    Returns:
        ConnectorService: The ConnectorService instance for multi-source search.
    """
    from langflow.connectors.factory import ConnectorServiceFactory

    return get_service(ServiceType.CONNECTOR_SERVICE, ConnectorServiceFactory())


def get_streaming_service():
    """Retrieves the VercelStreamingService instance from the service manager.

    Returns:
        VercelStreamingService: The streaming service instance for Vercel AI protocol.
    """
    from langflow.services.streaming.factory import VercelStreamingServiceFactory

    return get_service(ServiceType.STREAMING_SERVICE, VercelStreamingServiceFactory())


def get_docling_service():
    """Retrieves the DoclingService instance from the service manager.

    Returns:
        DoclingService: The DoclingService instance for document processing.
    """
    from langflow.services.docling.factory import DoclingServiceFactory

    return get_service(ServiceType.DOCLING_SERVICE, DoclingServiceFactory())


def get_page_limit_service():
    """Retrieves the PageLimitService instance from the service manager.

    Returns:
        PageLimitService: The PageLimitService instance for page quota management.
    """
    from langflow.services.page_limit.factory import PageLimitServiceFactory

    return get_service(ServiceType.PAGE_LIMIT_SERVICE, PageLimitServiceFactory())


def get_stt_service():
    """Retrieves the STTService instance from the service manager.

    Returns:
        STTService: The STTService instance for speech-to-text.
    """
    from langflow.services.stt.factory import STTServiceFactory

    return get_service(ServiceType.STT_SERVICE, STTServiceFactory())


def get_tts_service():
    """Retrieves the TTSService instance from the service manager.

    Returns:
        TTSService: The TTSService instance for text-to-speech.
    """
    from langflow.services.tts.factory import TTSServiceFactory

    return get_service(ServiceType.TTS_SERVICE, TTSServiceFactory())
