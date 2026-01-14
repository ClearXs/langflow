"""Holo knowledge system connectors module.

Provides connectors for integrating with various external data sources.

NOTE: Some connectors have dependencies on SurfSense-specific schemas.
These will be imported conditionally and may require additional adaptation.
Core connectors (GitHub, Notion, Slack) are standalone and work immediately.
"""

__all__ = []

# Core connectors - standalone, no schema dependencies
try:
    from .github_connector import GitHubConnector
    __all__.append("GitHubConnector")
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import GitHubConnector: {e}")

try:
    from .notion_history import NotionHistoryConnector
    __all__.append("NotionHistoryConnector")
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import NotionHistoryConnector: {e}")

try:
    from .slack_history import SlackHistory
    __all__.append("SlackHistory")
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import SlackHistory: {e}")

try:
    from .discord_connector import DiscordConnector
    __all__.append("DiscordConnector")
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import DiscordConnector: {e}")

try:
    from .webcrawler_connector import WebCrawlerConnector
    __all__.append("WebCrawlerConnector")
except ImportError as e:
    import warnings
    warnings.warn(f"Could not import WebCrawlerConnector: {e}")

# Connectors with schema dependencies - may need adaptation
try:
    from .airtable_connector import AirtableConnector
    __all__.append("AirtableConnector")
except ImportError:
    pass

try:
    from .bookstack_connector import BookStackConnector
    __all__.append("BookStackConnector")
except ImportError:
    pass

try:
    from .clickup_connector import ClickUpConnector
    __all__.append("ClickUpConnector")
except ImportError:
    pass

try:
    from .confluence_connector import ConfluenceConnector
    __all__.append("ConfluenceConnector")
except ImportError:
    pass

try:
    from .elasticsearch_connector import ElasticsearchConnector
    __all__.append("ElasticsearchConnector")
except ImportError:
    pass

try:
    from .google_calendar_connector import GoogleCalendarConnector
    __all__.append("GoogleCalendarConnector")
except ImportError:
    pass

try:
    from .google_gmail_connector import GoogleGmailConnector
    __all__.append("GoogleGmailConnector")
except ImportError:
    pass

try:
    from .jira_connector import JiraConnector
    __all__.append("JiraConnector")
except ImportError:
    pass

try:
    from .linear_connector import LinearConnector
    __all__.append("LinearConnector")
except ImportError:
    pass

try:
    from .luma_connector import LumaConnector
    __all__.append("LumaConnector")
except ImportError:
    pass
