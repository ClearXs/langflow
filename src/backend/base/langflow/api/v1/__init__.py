from langflow.api.v1.api_key import router as api_key_router
from langflow.api.v1.chat import router as chat_router
from langflow.api.v1.chats import router as chats_router
from langflow.api.v1.connector_oauth_airtable import router as connector_oauth_airtable_router
from langflow.api.v1.connector_oauth_gmail import router as connector_oauth_gmail_router
from langflow.api.v1.connector_oauth_google_calendar import router as connector_oauth_google_calendar_router
from langflow.api.v1.connector_oauth_luma import router as connector_oauth_luma_router
from langflow.api.v1.connectors import router as connectors_router
from langflow.api.v1.documents import router as documents_router
from langflow.api.v1.editor import router as editor_router
from langflow.api.v1.endpoints import router as endpoints_router
from langflow.api.v1.entities import router as entities_router
from langflow.api.v1.files import router as files_router
from langflow.api.v1.flows import router as flows_router
from langflow.api.v1.folders import router as folders_router

# GDB router is optional (requires GDAL)
try:
    from langflow.api.v1.gdb import router as gdb_router
    GDB_AVAILABLE = True
except ImportError:
    gdb_router = None
    GDB_AVAILABLE = False

from langflow.api.v1.graphs import router as graphs_router
from langflow.api.v1.knowledge_bases import router as knowledge_bases_router
from langflow.api.v1.lineage import lineage_router as lineage_search_router
from langflow.api.v1.lineage import router as lineage_router
from langflow.api.v1.llm_configs import router as llm_configs_router
from langflow.api.v1.i18n_api import router as locale_router
from langflow.api.v1.login import router as login_router
from langflow.api.v1.logs import router as logs_router
from langflow.api.v1.mcp import router as mcp_router
from langflow.api.v1.mcp_projects import router as mcp_projects_router
from langflow.api.v1.monitor import router as monitor_router
from langflow.api.v1.notes import router as notes_router
from langflow.api.v1.openai_responses import router as openai_responses_router
from langflow.api.v1.podcasts import router as podcasts_router
from langflow.api.v1.projects import router as projects_router
from langflow.api.v1.rbac import router as rbac_router
from langflow.api.v1.spaces import router as spaces_router
from langflow.api.v1.starter_projects import router as starter_projects_router
from langflow.api.v1.store import router as store_router
from langflow.api.v1.tasks import router as tasks_router
from langflow.api.v1.users import router as users_router
from langflow.api.v1.validate import router as validate_router
from langflow.api.v1.variable import router as variables_router
from langflow.api.v1.voice_mode import router as voice_mode_router

__all__ = [
    "GDB_AVAILABLE",
    "api_key_router",
    "chat_router",
    "chats_router",
    "connector_oauth_airtable_router",
    "connector_oauth_gmail_router",
    "connector_oauth_google_calendar_router",
    "connector_oauth_luma_router",
    "connectors_router",
    "documents_router",
    "editor_router",
    "endpoints_router",
    "entities_router",
    "files_router",
    "flows_router",
    "folders_router",
    "gdb_router",
    "graphs_router",
    "knowledge_bases_router",
    "lineage_router",
    "lineage_search_router",
    "llm_configs_router",
    "locale_router",
    "login_router",
    "logs_router",
    "mcp_projects_router",
    "mcp_router",
    "monitor_router",
    "notes_router",
    "openai_responses_router",
    "podcasts_router",
    "projects_router",
    "rbac_router",
    "spaces_router",
    "starter_projects_router",
    "store_router",
    "tasks_router",
    "users_router",
    "validate_router",
    "variables_router",
    "voice_mode_router",
]
