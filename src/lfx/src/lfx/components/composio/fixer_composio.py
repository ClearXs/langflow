from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioFixerAPIComponent(ComposioBaseComponent):
    display_name: str = "Fixer"
    icon = "Fixer"
    documentation: str = "https://docs.composio.dev"
    app_name = "fixer"

    ignore: bool = True

    def set_default_tools(self):
        """Set the default tools for Fixer component."""
