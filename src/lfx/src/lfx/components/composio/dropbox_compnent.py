import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioDropboxAPIComponent(ComposioBaseComponent):
    display_name: str = "Dropbox"
    icon = "Dropbox"
    documentation: str = "https://docs.composio.dev"
    app_name = "dropbox"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Dropbox component."""
