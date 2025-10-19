from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioAgiledAPIComponent(ComposioBaseComponent):
    display_name: str = "Agiled"
    icon = "Agiled"
    documentation: str = "https://docs.composio.dev"
    app_name = "agiled"

    ignore: bool = True

    def set_default_tools(self):
        """Set the default tools for Agiled component."""
