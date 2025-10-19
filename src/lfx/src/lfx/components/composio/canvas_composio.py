from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioCanvasAPIComponent(ComposioBaseComponent):
    display_name: str = "Canvas"
    icon = "Canvas"
    documentation: str = "https://docs.composio.dev"
    app_name = "canvas"

    ignore: bool = True

    def set_default_tools(self):
        """Set the default tools for Canvaas component."""
