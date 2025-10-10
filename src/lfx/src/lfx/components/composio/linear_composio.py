import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioLinearAPIComponent(ComposioBaseComponent):
    display_name: str = "Linear"
    icon = "Linear"
    documentation: str = "https://docs.composio.dev"
    app_name = "linear"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Linear component."""
