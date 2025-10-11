import os
from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioYoutubeAPIComponent(ComposioBaseComponent):
    display_name: str = "Youtube"
    icon = "Youtube"
    documentation: str = "https://docs.composio.dev"
    app_name = "youtube"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def set_default_tools(self):
        """Set the default tools for Youtube component."""
