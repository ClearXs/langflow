import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioOutlookAPIComponent(ComposioBaseComponent):
    display_name: str = "Outlook"
    icon = "Outlook"
    documentation: str = "https://docs.composio.dev"
    app_name = "outlook"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Outlook component."""
