from lfx.base.composio.composio_base import ComposioBaseComponent


class ComposioGitHubAPIComponent(ComposioBaseComponent):
    display_name: str = "GitHub"
    icon = "Github"
    documentation: str = "https://docs.composio.dev"
    app_name = "github"

    ignore: bool = True

    def set_default_tools(self):
        """Set the default tools for GitHub component."""
