import i18n
from spider.spider import Spider

from lfx.base.langchain_utilities.spider_constants import MODES
from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DictInput,
    DropdownInput,
    IntInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class SpiderTool(Component):
    display_name: str = i18n.t(
        'components.langchain_utilities.spider.display_name')
    description: str = i18n.t(
        'components.langchain_utilities.spider.description')
    output_types: list[str] = ["Document"]
    documentation: str = "https://spider.cloud/docs/api"

    inputs = [
        SecretStrInput(
            name="spider_api_key",
            display_name=i18n.t(
                'components.langchain_utilities.spider.spider_api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.langchain_utilities.spider.spider_api_key.info'),
        ),
        StrInput(
            name="url",
            display_name=i18n.t(
                'components.langchain_utilities.spider.url.display_name'),
            required=True,
            info=i18n.t('components.langchain_utilities.spider.url.info'),
        ),
        DropdownInput(
            name="mode",
            display_name=i18n.t(
                'components.langchain_utilities.spider.mode.display_name'),
            required=True,
            options=MODES,
            value=MODES[0],
            info=i18n.t('components.langchain_utilities.spider.mode.info'),
        ),
        IntInput(
            name="limit",
            display_name=i18n.t(
                'components.langchain_utilities.spider.limit.display_name'),
            info=i18n.t('components.langchain_utilities.spider.limit.info'),
            advanced=True,
        ),
        IntInput(
            name="depth",
            display_name=i18n.t(
                'components.langchain_utilities.spider.depth.display_name'),
            info=i18n.t('components.langchain_utilities.spider.depth.info'),
            advanced=True,
        ),
        StrInput(
            name="blacklist",
            display_name=i18n.t(
                'components.langchain_utilities.spider.blacklist.display_name'),
            info=i18n.t(
                'components.langchain_utilities.spider.blacklist.info'),
            advanced=True,
        ),
        StrInput(
            name="whitelist",
            display_name=i18n.t(
                'components.langchain_utilities.spider.whitelist.display_name'),
            info=i18n.t(
                'components.langchain_utilities.spider.whitelist.info'),
            advanced=True,
        ),
        BoolInput(
            name="readability",
            display_name=i18n.t(
                'components.langchain_utilities.spider.readability.display_name'),
            info=i18n.t(
                'components.langchain_utilities.spider.readability.info'),
            advanced=True,
        ),
        IntInput(
            name="request_timeout",
            display_name=i18n.t(
                'components.langchain_utilities.spider.request_timeout.display_name'),
            info=i18n.t(
                'components.langchain_utilities.spider.request_timeout.info'),
            advanced=True,
        ),
        BoolInput(
            name="metadata",
            display_name=i18n.t(
                'components.langchain_utilities.spider.metadata.display_name'),
            info=i18n.t('components.langchain_utilities.spider.metadata.info'),
            advanced=True,
        ),
        DictInput(
            name="params",
            display_name=i18n.t(
                'components.langchain_utilities.spider.params.display_name'),
            info=i18n.t('components.langchain_utilities.spider.params.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.langchain_utilities.spider.outputs.content.display_name'),
            name="content",
            method="crawl"
        ),
    ]

    def crawl(self) -> list[Data]:
        if self.params:
            parameters = self.params["data"]
        else:
            parameters = {
                "limit": self.limit or None,
                "depth": self.depth or None,
                "blacklist": self.blacklist or None,
                "whitelist": self.whitelist or None,
                "readability": self.readability,
                "request_timeout": self.request_timeout or None,
                "metadata": self.metadata,
                "return_format": "markdown",
            }

        app = Spider(api_key=self.spider_api_key)
        if self.mode == "scrape":
            parameters["limit"] = 1
            result = app.scrape_url(self.url, parameters)
        elif self.mode == "crawl":
            result = app.crawl_url(self.url, parameters)
        else:
            msg = f"Invalid mode: {self.mode}. Must be 'scrape' or 'crawl'."
            raise ValueError(msg)

        records = []

        for record in result:
            if self.metadata:
                records.append(
                    Data(
                        data={
                            "content": record["content"],
                            "url": record["url"],
                            "metadata": record["metadata"],
                        }
                    )
                )
            else:
                records.append(
                    Data(data={"content": record["content"], "url": record["url"]}))
        return records


class SpiderToolError(Exception):
    """SpiderTool error."""
