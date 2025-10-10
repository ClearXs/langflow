import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioGoogleSheetsAPIComponent(ComposioBaseComponent):
    display_name: str = "Google Sheets"
    icon = "Googlesheets"
    documentation: str = "https://docs.composio.dev"
    app_name = "googlesheets"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Google Sheets component."""
