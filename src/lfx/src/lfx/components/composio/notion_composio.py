import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioNotionAPIComponent(ComposioBaseComponent):
    display_name: str = "Notion"
    icon = "Notion"
    documentation: str = "https://docs.composio.dev"
    app_name = "notion"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Notion component."""
