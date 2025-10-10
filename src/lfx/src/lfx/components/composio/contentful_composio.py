import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioContentfulAPIComponent(ComposioBaseComponent):
    display_name: str = "Contentful"
    icon = "Contentful"
    documentation: str = "https://docs.composio.dev"
    app_name = "contentful"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Contentful component."""
