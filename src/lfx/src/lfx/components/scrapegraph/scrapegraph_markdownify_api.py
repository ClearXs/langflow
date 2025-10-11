import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import (
    MessageTextInput,
    Output,
    SecretStrInput,
)
from lfx.schema.data import Data


class ScrapeGraphMarkdownifyApi(Component):
    display_name: str = i18n.t(
        'components.scrapegraph.scrapegraph_markdownify_api.display_name')
    description: str = i18n.t(
        'components.scrapegraph.scrapegraph_markdownify_api.description')
    name = "ScrapeGraphMarkdownifyApi"

    output_types: list[str] = ["Document"]
    documentation: str = "https://docs.scrapegraphai.com/services/markdownify"
    icon = "ScrapeGraph"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.scrapegraph.scrapegraph_markdownify_api.api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.scrapegraph.scrapegraph_markdownify_api.api_key.info'),
        ),
        MessageTextInput(
            name="url",
            display_name=i18n.t(
                'components.scrapegraph.scrapegraph_markdownify_api.url.display_name'),
            tool_mode=True,
            info=i18n.t(
                'components.scrapegraph.scrapegraph_markdownify_api.url.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.scrapegraph.scrapegraph_markdownify_api.outputs.data.display_name'),
            name="data",
            method="scrape"
        ),
    ]

    def scrape(self) -> list[Data]:
        try:
            from scrapegraph_py import Client
            from scrapegraph_py.logger import sgai_logger
        except ImportError as e:
            msg = "Could not import scrapegraph-py package. Please install it with `pip install scrapegraph-py`."
            raise ImportError(msg) from e

        # Set logging level
        sgai_logger.set_logging(level="INFO")

        # Initialize the client with API key
        sgai_client = Client(api_key=self.api_key)

        try:
            # Markdownify request
            response = sgai_client.markdownify(
                website_url=self.url,
            )

            # Close the client
            sgai_client.close()

            return Data(data=response)
        except Exception:
            sgai_client.close()
            raise
