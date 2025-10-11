import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioSlackbotAPIComponent(ComposioBaseComponent):
    display_name: str = "Slackbot"
    icon = "Slack"
    documentation: str = "https://docs.composio.dev"
    app_name = "slackbot"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Slackbot component."""
