import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import (
    DataInput,
    IntInput,
    MultilineInput,
    Output,
    SecretStrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class FirecrawlScrapeApi(Component):
    display_name: str = "Firecrawl Scrape API"
    description: str = i18n.t(
        'components.firecrawl.firecrawl_scrape_api.description')
    name = "FirecrawlScrapeApi"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    documentation: str = "https://docs.firecrawl.dev/api-reference/endpoint/scrape"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.api_key.info'),
        ),
        MultilineInput(
            name="url",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.url.display_name'),
            required=True,
            info=i18n.t('components.firecrawl.firecrawl_scrape_api.url.info'),
            tool_mode=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.timeout.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.timeout.info'),
        ),
        DataInput(
            name="scrapeOptions",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.scrapeOptions.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.scrapeOptions.info'),
        ),
        DataInput(
            name="extractorOptions",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.extractorOptions.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.extractorOptions.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.firecrawl.firecrawl_scrape_api.outputs.data.display_name'),
            name="data",
            method="scrape"
        ),
    ]

    def scrape(self) -> Data:
        """Scrape a URL and extract its content using Firecrawl API.

        Returns:
            Data: Data object containing the scraped content.

        Raises:
            ImportError: If firecrawl-py package is not installed.
            ValueError: If URL is missing or scraping fails.
        """
        try:
            from firecrawl import FirecrawlApp
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_scrape_api.logs.firecrawl_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_scrape_api.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        # Validate URL
        if not self.url or not self.url.strip():
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_scrape_api.errors.url_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.firecrawl.firecrawl_scrape_api.logs.starting_scrape',
                           url=self.url))

        # Prepare scrape options
        params = self.scrapeOptions.__dict__.get(
            "data", {}) if self.scrapeOptions else {}
        extractor_options_dict = self.extractorOptions.__dict__.get(
            "data", {}) if self.extractorOptions else {}

        if extractor_options_dict:
            params["extract"] = extractor_options_dict
            logger.debug(i18n.t(
                'components.firecrawl.firecrawl_scrape_api.logs.extractor_options_added'))

        # Set default values for parameters
        params.setdefault("formats", ["markdown"])  # Default output format
        # Default to only main content
        params.setdefault("onlyMainContent", True)

        logger.debug(i18n.t('components.firecrawl.firecrawl_scrape_api.logs.params_configured',
                            formats=params.get("formats", []),
                            only_main=params.get("onlyMainContent", True)))

        try:
            app = FirecrawlApp(api_key=self.api_key)
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_scrape_api.logs.app_initialized'))

            logger.info(
                i18n.t('components.firecrawl.firecrawl_scrape_api.logs.executing_scrape'))
            results = app.scrape_url(self.url, params=params)

            # Log results summary
            content_length = 0
            if isinstance(results, dict):
                if "markdown" in results:
                    content_length = len(results.get("markdown", ""))
                elif "content" in results:
                    content_length = len(results.get("content", ""))

            logger.info(i18n.t('components.firecrawl.firecrawl_scrape_api.logs.scrape_completed',
                               length=content_length))

            result_data = Data(data=results)
            self.status = {"url": self.url, "content_length": content_length}

            return result_data

        except Exception as e:
            error_msg = i18n.t('components.firecrawl.firecrawl_scrape_api.errors.scrape_failed',
                               url=self.url,
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
