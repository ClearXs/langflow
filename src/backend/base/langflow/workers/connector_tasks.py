"""Celery tasks for connector indexing."""

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from langflow.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_celery_session_maker():
    """Create a new async session maker for Celery tasks.
    This is necessary because Celery tasks run in a new event loop,
    and the default session maker is bound to the main app's event loop.
    """
    from langflow.services.deps import get_settings_service

    settings_service = get_settings_service()
    settings = settings_service.settings

    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,  # Don't use connection pooling for Celery tasks
        echo=False,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="langflow.workers.index_slack_messages", bind=True)
def index_slack_messages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Slack messages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_slack_messages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_slack_messages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Slack messages with new session."""
    from langflow.indexers.slack_indexer import index_slack_messages

    async with get_celery_session_maker()() as session:
        await index_slack_messages(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_notion_pages", bind=True)
def index_notion_pages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Notion pages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_notion_pages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_notion_pages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Notion pages with new session."""
    from langflow.indexers.notion_indexer import index_notion_pages

    async with get_celery_session_maker()() as session:
        await index_notion_pages(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_github_repos", bind=True)
def index_github_repos_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index GitHub repositories."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_github_repos(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_github_repos(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index GitHub repositories with new session."""
    from langflow.indexers.github_indexer import index_github_repos

    async with get_celery_session_maker()() as session:
        await index_github_repos(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_linear_issues", bind=True)
def index_linear_issues_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Linear issues."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_linear_issues(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_linear_issues(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Linear issues with new session."""
    from langflow.indexers.linear_indexer import index_linear_issues

    async with get_celery_session_maker()() as session:
        await index_linear_issues(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_jira_issues", bind=True)
def index_jira_issues_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Jira issues."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_jira_issues(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_jira_issues(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Jira issues with new session."""
    from langflow.indexers.jira_indexer import index_jira_issues

    async with get_celery_session_maker()() as session:
        await index_jira_issues(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_confluence_pages", bind=True)
def index_confluence_pages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Confluence pages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_confluence_pages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_confluence_pages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Confluence pages with new session."""
    from langflow.indexers.confluence_indexer import index_confluence_pages

    async with get_celery_session_maker()() as session:
        await index_confluence_pages(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_clickup_tasks", bind=True)
def index_clickup_tasks_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index ClickUp tasks."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_clickup_tasks(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_clickup_tasks(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index ClickUp tasks with new session."""
    from langflow.indexers.clickup_indexer import index_clickup_tasks

    async with get_celery_session_maker()() as session:
        await index_clickup_tasks(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_google_calendar_events", bind=True)
def index_google_calendar_events_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Google Calendar events."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_google_calendar_events(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_google_calendar_events(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Google Calendar events with new session."""
    from langflow.indexers.google_calendar_indexer import index_google_calendar_events

    async with get_celery_session_maker()() as session:
        await index_google_calendar_events(
            session, connector_id, space_id, user_id, start_date, end_date
        )


@celery_app.task(name="langflow.workers.index_airtable_records", bind=True)
def index_airtable_records_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Airtable records."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_airtable_records(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_airtable_records(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Airtable records with new session."""
    from langflow.indexers.airtable_indexer import index_airtable_records

    async with get_celery_session_maker()() as session:
        await index_airtable_records(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_google_gmail_messages", bind=True)
def index_google_gmail_messages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Google Gmail messages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_google_gmail_messages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_google_gmail_messages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Google Gmail messages with new session."""
    from datetime import datetime

    from langflow.indexers.google_gmail_indexer import index_google_gmail_messages

    # Parse dates to calculate days_back
    max_messages = 100
    days_back = 30  # Default

    if start_date:
        try:
            # Parse start_date (format: YYYY-MM-DD)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            # Calculate days back from now
            days_back = (datetime.now() - start_dt).days
            # Ensure at least 1 day
            days_back = max(1, days_back)
        except ValueError:
            # If parsing fails, use default
            days_back = 30

    async with get_celery_session_maker()() as session:
        await index_google_gmail_messages(
            session, connector_id, space_id, user_id, max_messages, days_back
        )


@celery_app.task(name="langflow.workers.index_discord_messages", bind=True)
def index_discord_messages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Discord messages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_discord_messages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_discord_messages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Discord messages with new session."""
    from langflow.indexers.discord_indexer import index_discord_messages

    async with get_celery_session_maker()() as session:
        await index_discord_messages(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_luma_events", bind=True)
def index_luma_events_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Luma events."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_luma_events(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_luma_events(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Luma events with new session."""
    from langflow.indexers.luma_indexer import index_luma_events

    async with get_celery_session_maker()() as session:
        await index_luma_events(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_elasticsearch_documents", bind=True)
def index_elasticsearch_documents_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Elasticsearch documents."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_elasticsearch_documents(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_elasticsearch_documents(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Elasticsearch documents with new session."""
    from langflow.indexers.elasticsearch_indexer import index_elasticsearch_documents

    async with get_celery_session_maker()() as session:
        await index_elasticsearch_documents(
            session, connector_id, space_id, user_id, start_date, end_date
        )


@celery_app.task(name="langflow.workers.index_crawled_urls", bind=True)
def index_crawled_urls_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index Web page Urls."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_crawled_urls(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_crawled_urls(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index Web page Urls with new session."""
    from langflow.indexers.webcrawler_indexer import index_crawled_urls

    async with get_celery_session_maker()() as session:
        await index_crawled_urls(session, connector_id, space_id, user_id, start_date, end_date)


@celery_app.task(name="langflow.workers.index_bookstack_pages", bind=True)
def index_bookstack_pages_task(
    self,
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Celery task to index BookStack pages."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(
            _index_bookstack_pages(connector_id, space_id, user_id, start_date, end_date)
        )
    finally:
        loop.close()


async def _index_bookstack_pages(
    connector_id: int,
    space_id: int,
    user_id: str,
    start_date: str,
    end_date: str,
):
    """Index BookStack pages with new session."""
    from langflow.indexers.bookstack_indexer import index_bookstack_pages

    async with get_celery_session_maker()() as session:
        await index_bookstack_pages(session, connector_id, space_id, user_id, start_date, end_date)


# TODO: Uncomment when google_drive_indexer is implemented
# @celery_app.task(name="langflow.workers.index_google_drive_files", bind=True)
# def index_google_drive_files_task(
#     self,
#     connector_id: int,
#     space_id: int,
#     user_id: str,
#     start_date: str,
#     end_date: str,
# ):
#     """Celery task to index Google Drive files."""
#     import asyncio
#
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     try:
#         loop.run_until_complete(
#             _index_google_drive_files(connector_id, space_id, user_id, start_date, end_date)
#         )
#     finally:
#         loop.close()
#
#
# async def _index_google_drive_files(
#     connector_id: int,
#     space_id: int,
#     user_id: str,
#     start_date: str,
#     end_date: str,
# ):
#     """Index Google Drive files with new session."""
#     from langflow.indexers.google_drive_indexer import index_google_drive_files
#
#     async with get_celery_session_maker()() as session:
#         await index_google_drive_files(
#             session, connector_id, space_id, user_id, start_date, end_date
#         )
