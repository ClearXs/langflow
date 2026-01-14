from enum import Enum


class ServiceType(str, Enum):
    """Enum for the different types of services that can be registered with the service manager."""

    AUTH_SERVICE = "auth_service"
    CACHE_SERVICE = "cache_service"
    SHARED_COMPONENT_CACHE_SERVICE = "shared_component_cache_service"
    SETTINGS_SERVICE = "settings_service"
    DATABASE_SERVICE = "database_service"
    CHAT_SERVICE = "chat_service"
    SESSION_SERVICE = "session_service"
    TASK_SERVICE = "task_service"
    STORE_SERVICE = "store_service"
    VARIABLE_SERVICE = "variable_service"
    STORAGE_SERVICE = "storage_service"
    STATE_SERVICE = "state_service"
    TRACING_SERVICE = "tracing_service"
    TELEMETRY_SERVICE = "telemetry_service"
    JOB_QUEUE_SERVICE = "job_queue_service"
    MCP_COMPOSER_SERVICE = "mcp_composer_service"
    NACOS_SERVICE = "nacos_service"
    # Holo Knowledge System Services
    LLM_SERVICE = "llm_service"
    TASK_LOGGING_SERVICE = "task_logging_service"
    QUERY_SERVICE = "query_service"
    RERANKER_SERVICE = "reranker_service"
    CONNECTOR_SERVICE = "connector_service"
    STREAMING_SERVICE = "streaming_service"
    DOCLING_SERVICE = "docling_service"
    PAGE_LIMIT_SERVICE = "page_limit_service"
    STT_SERVICE = "stt_service"
    TTS_SERVICE = "tts_service"
