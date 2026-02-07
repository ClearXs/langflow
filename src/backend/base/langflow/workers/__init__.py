"""Celery workers for background task processing."""

from langflow.workers.connector_sync import sync_all_connectors_task, sync_connector_task
from langflow.workers.connector_tasks import (
    index_airtable_records_task,
    index_bookstack_pages_task,
    index_clickup_tasks_task,
    index_confluence_pages_task,
    index_crawled_urls_task,
    index_discord_messages_task,
    index_elasticsearch_documents_task,
    index_github_repos_task,
    index_google_calendar_events_task,
    index_google_gmail_messages_task,
    index_jira_issues_task,
    index_linear_issues_task,
    index_luma_events_task,
    index_notion_pages_task,
    index_slack_messages_task,
)
from langflow.workers.document_tasks import (
    process_extension_document_task,
    process_file_upload_task,
    process_youtube_video_task,
)

__all__ = [
    # Connector sync tasks
    "sync_connector_task",
    "sync_all_connectors_task",
    # Connector tasks
    "index_airtable_records_task",
    "index_bookstack_pages_task",
    "index_clickup_tasks_task",
    "index_confluence_pages_task",
    "index_crawled_urls_task",
    "index_discord_messages_task",
    "index_elasticsearch_documents_task",
    "index_github_repos_task",
    "index_google_calendar_events_task",
    "index_google_gmail_messages_task",
    "index_jira_issues_task",
    "index_linear_issues_task",
    "index_luma_events_task",
    "index_notion_pages_task",
    "index_slack_messages_task",
    # Document tasks
    "process_extension_document_task",
    "process_file_upload_task",
    "process_youtube_video_task",
]
