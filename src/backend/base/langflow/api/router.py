# Router for base api
from fastapi import APIRouter

from langflow.api.v1 import (
    GDB_AVAILABLE,
    api_key_router,
    chat_router,
    chats_router,
    connector_oauth_airtable_router,
    connector_oauth_gmail_router,
    connector_oauth_google_calendar_router,
    connector_oauth_luma_router,
    connectors_router,
    documents_router,
    editor_router,
    endpoints_router,
    entities_router,
    files_router,
    flows_router,
    folders_router,
    gdb_router,
    graphs_router,
    knowledge_bases_router,
    lineage_router,
    lineage_search_router,
    llm_configs_router,
    locale_router,
    login_router,
    logs_router,
    mcp_projects_router,
    mcp_router,
    monitor_router,
    notes_router,
    openai_responses_router,
    podcasts_router,
    projects_router,
    rbac_router,
    spaces_router,
    starter_projects_router,
    store_router,
    tasks_router,
    users_router,
    validate_router,
    variables_router,
)
from langflow.api.v1.voice_mode import router as voice_mode_router
from langflow.api.v2 import files_router as files_router_v2
from langflow.api.v2 import mcp_router as mcp_router_v2

router_v1 = APIRouter(
    prefix="/v1",
)

router_v2 = APIRouter(
    prefix="/v2",
)

router_v1.include_router(chat_router)
router_v1.include_router(chats_router)
router_v1.include_router(connector_oauth_airtable_router)
router_v1.include_router(connector_oauth_gmail_router)
router_v1.include_router(connector_oauth_google_calendar_router)
router_v1.include_router(connector_oauth_luma_router)
router_v1.include_router(connectors_router)
router_v1.include_router(documents_router)
router_v1.include_router(editor_router)
router_v1.include_router(endpoints_router)
router_v1.include_router(entities_router)
router_v1.include_router(entities_router, prefix="/graph")
router_v1.include_router(validate_router)
router_v1.include_router(store_router)
router_v1.include_router(flows_router)
router_v1.include_router(users_router)
router_v1.include_router(api_key_router)
router_v1.include_router(login_router)
router_v1.include_router(variables_router)
router_v1.include_router(files_router)
router_v1.include_router(monitor_router)
router_v1.include_router(folders_router)
router_v1.include_router(projects_router)
router_v1.include_router(starter_projects_router)
router_v1.include_router(graphs_router)
router_v1.include_router(knowledge_bases_router)
router_v1.include_router(lineage_router)
router_v1.include_router(lineage_search_router)
router_v1.include_router(llm_configs_router)
router_v1.include_router(logs_router)
router_v1.include_router(mcp_router)
router_v1.include_router(voice_mode_router)
router_v1.include_router(mcp_projects_router)
router_v1.include_router(notes_router)
router_v1.include_router(openai_responses_router)
router_v1.include_router(podcasts_router)
router_v1.include_router(rbac_router)
router_v1.include_router(spaces_router)
router_v1.include_router(locale_router)
router_v1.include_router(tasks_router)

# Only include GDB router if GDAL is available
if GDB_AVAILABLE:
    router_v1.include_router(gdb_router)

router_v2.include_router(files_router_v2)
router_v2.include_router(mcp_router_v2)

router = APIRouter(
    prefix="/api",
)
router.include_router(router_v1)
router.include_router(router_v2)
