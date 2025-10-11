import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioAsanaAPIComponent(ComposioBaseComponent):
    display_name: str = "Asana"
    icon = "Asana"
    documentation: str = "https://docs.composio.dev"
    app_name = "asana"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Asana component."""
