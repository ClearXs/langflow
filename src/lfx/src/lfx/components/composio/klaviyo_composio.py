import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioKlaviyoAPIComponent(ComposioBaseComponent):
    display_name: str = "Klaviyo"
    icon = "Klaviyo"
    documentation: str = "https://docs.composio.dev"
    app_name = "klaviyo"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Klaviyo component."""
