import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioRedditAPIComponent(ComposioBaseComponent):
    display_name: str = "Reddit"
    icon = "Reddit"
    documentation: str = "https://docs.composio.dev"
    app_name = "reddit"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Reddit component."""
