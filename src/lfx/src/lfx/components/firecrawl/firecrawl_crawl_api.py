import i18n
import uuid

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, IntInput, MultilineInput, Output, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class FirecrawlCrawlApi(Component):
    display_name: str = "Firecrawl Crawl API"
    description: str = i18n.t(
        'components.firecrawl.firecrawl_crawl_api.description')
    name = "FirecrawlCrawlApi"

    documentation: str = "https://docs.firecrawl.dev/v1/api-reference/endpoint/crawl-post"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.api_key.info'),
        ),
        MultilineInput(
            name="url",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.url.display_name'),
            required=True,
            info=i18n.t('components.firecrawl.firecrawl_crawl_api.url.info'),
            tool_mode=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.timeout.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.timeout.info'),
        ),
        StrInput(
            name="idempotency_key",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.idempotency_key.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.idempotency_key.info'),
        ),
        DataInput(
            name="crawlerOptions",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.crawlerOptions.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.crawlerOptions.info'),
        ),
        DataInput(
            name="scrapeOptions",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.scrapeOptions.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.scrapeOptions.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.firecrawl.firecrawl_crawl_api.outputs.data.display_name'),
            name="data",
            method="crawl"
        ),
    ]
    idempotency_key: str | None = None

    def crawl(self) -> Data:
        """Crawl a URL and all its subpages using Firecrawl API.

        Returns:
            Data: Data object containing the crawl results.

        Raises:
            ImportError: If firecrawl-py package is not installed.
            ValueError: If the crawl operation fails.
        """
        try:
            from firecrawl import FirecrawlApp
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_crawl_api.logs.firecrawl_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_crawl_api.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        logger.info(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.starting_crawl',
                           url=self.url))

        # Prepare crawler options
        params = self.crawlerOptions.__dict__[
            "data"] if self.crawlerOptions else {}
        scrape_options_dict = self.scrapeOptions.__dict__[
            "data"] if self.scrapeOptions else {}

        if scrape_options_dict:
            params["scrapeOptions"] = scrape_options_dict
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_crawl_api.logs.scrape_options_added'))

        # Set default values for new parameters in v1
        params.setdefault("maxDepth", 2)
        params.setdefault("limit", 10000)
        params.setdefault("allowExternalLinks", False)
        params.setdefault("allowBackwardLinks", False)
        params.setdefault("ignoreSitemap", False)
        params.setdefault("ignoreQueryParameters", False)

        logger.debug(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.default_params_set',
                            max_depth=params["maxDepth"],
                            limit=params["limit"]))

        # Ensure onlyMainContent is explicitly set if not provided
        if "scrapeOptions" in params:
            params["scrapeOptions"].setdefault("onlyMainContent", True)
        else:
            params["scrapeOptions"] = {"onlyMainContent": True}

        logger.debug(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.main_content_only',
                            enabled=params["scrapeOptions"]["onlyMainContent"]))

        # Generate idempotency key if not provided
        if not self.idempotency_key:
            self.idempotency_key = str(uuid.uuid4())
            logger.debug(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.idempotency_key_generated',
                                key=self.idempotency_key))
        else:
            logger.debug(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.idempotency_key_provided',
                                key=self.idempotency_key))

        try:
            app = FirecrawlApp(api_key=self.api_key)
            logger.info(i18n.t(
                'components.firecrawl.firecrawl_crawl_api.logs.firecrawl_app_initialized'))

            logger.info(
                i18n.t('components.firecrawl.firecrawl_crawl_api.logs.executing_crawl'))
            crawl_result = app.crawl_url(
                self.url,
                params=params,
                idempotency_key=self.idempotency_key
            )

            # Count results if available
            result_count = len(crawl_result) if isinstance(crawl_result, list) else (
                len(crawl_result.get("data", [])) if isinstance(
                    crawl_result, dict) else 0
            )

            logger.info(i18n.t('components.firecrawl.firecrawl_crawl_api.logs.crawl_completed',
                               count=result_count))

            result_data = Data(data={"results": crawl_result})
            self.status = {"url": self.url, "result_count": result_count}

            return result_data

        except Exception as e:
            error_msg = i18n.t('components.firecrawl.firecrawl_crawl_api.errors.crawl_failed',
                               url=self.url,
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
