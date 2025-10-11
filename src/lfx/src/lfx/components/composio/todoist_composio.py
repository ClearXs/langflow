import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioTodoistAPIComponent(ComposioBaseComponent):
    display_name: str = "Todoist"
    icon = "Todoist"
    documentation: str = "https://docs.composio.dev"
    app_name = "todoist"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Todoist component."""
