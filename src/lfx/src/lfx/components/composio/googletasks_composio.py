import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioGoogleTasksAPIComponent(ComposioBaseComponent):
    display_name: str = "Google Tasks"
    icon = "GoogleTasks"
    documentation: str = "https://docs.composio.dev"
    app_name = "googletasks"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
