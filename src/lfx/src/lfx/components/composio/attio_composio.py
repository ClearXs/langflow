import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioAttioAPIComponent(ComposioBaseComponent):
    display_name: str = "Attio"
    icon = "Attio"
    documentation: str = "https://docs.composio.dev"
    app_name = "attio"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Attio component."""
