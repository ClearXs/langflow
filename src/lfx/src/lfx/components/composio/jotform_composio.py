from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioJotformAPIComponent(ComposioBaseComponent):
    display_name: str = "Jotform"
    icon = "Jotform"
    documentation: str = "https://docs.composio.dev"
    app_name = "jotform"

    ignore: bool = True

    def set_default_tools(self):
        """Set the default tools for Jotform component."""
