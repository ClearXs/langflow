import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    MultilineInput,
    Output,
    SecretStrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class FirecrawlMapApi(Component):
    display_name: str = "Firecrawl Map API"
    description: str = i18n.t(
        'components.firecrawl.firecrawl_map_api.description')
    name = "FirecrawlMapApi"

    documentation: str = "https://docs.firecrawl.dev/api-reference/endpoint/map"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t('components.firecrawl.firecrawl_map_api.api_key.info'),
        ),
        MultilineInput(
            name="urls",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.urls.display_name'),
            required=True,
            info=i18n.t('components.firecrawl.firecrawl_map_api.urls.info'),
            tool_mode=True,
        ),
        BoolInput(
            name="ignore_sitemap",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.ignore_sitemap.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_map_api.ignore_sitemap.info'),
        ),
        BoolInput(
            name="sitemap_only",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.sitemap_only.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_map_api.sitemap_only.info'),
        ),
        BoolInput(
            name="include_subdomains",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.include_subdomains.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_map_api.include_subdomains.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.firecrawl.firecrawl_map_api.outputs.data.display_name'),
            name="data",
            method="map"
        ),
    ]

    def map(self) -> Data:
        """Map URLs to discover all accessible links using Firecrawl API.

        Returns:
            Data: Data object containing all discovered links.

        Raises:
            ImportError: If firecrawl-py package is not installed.
            ValueError: If URLs are missing or invalid.
        """
        try:
            from firecrawl import FirecrawlApp
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_map_api.logs.firecrawl_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_map_api.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        # Validate URLs
        if not self.urls:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_map_api.errors.urls_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Split and validate URLs (handle both commas and newlines)
        logger.debug(
            i18n.t('components.firecrawl.firecrawl_map_api.logs.parsing_urls'))
        urls = [url.strip() for url in self.urls.replace(
            "\n", ",").split(",") if url.strip()]

        if not urls:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_map_api.errors.no_valid_urls')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.firecrawl.firecrawl_map_api.logs.urls_parsed',
                           count=len(urls)))

        params = {
            "ignoreSitemap": self.ignore_sitemap,
            "sitemapOnly": self.sitemap_only,
            "includeSubdomains": self.include_subdomains,
        }

        logger.debug(i18n.t('components.firecrawl.firecrawl_map_api.logs.params_configured',
                            ignore_sitemap=self.ignore_sitemap,
                            sitemap_only=self.sitemap_only,
                            include_subdomains=self.include_subdomains))

        try:
            app = FirecrawlApp(api_key=self.api_key)
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_map_api.logs.app_initialized'))

            # Map all provided URLs and combine results
            logger.info(i18n.t('components.firecrawl.firecrawl_map_api.logs.starting_mapping',
                               count=len(urls)))

            combined_links = []
            for idx, url in enumerate(urls, 1):
                logger.debug(i18n.t('components.firecrawl.firecrawl_map_api.logs.mapping_url',
                                    index=idx,
                                    total=len(urls),
                                    url=url))

                result = app.map_url(url, params=params)

                if isinstance(result, dict) and "links" in result:
                    link_count = len(result["links"])
                    combined_links.extend(result["links"])
                    logger.info(i18n.t('components.firecrawl.firecrawl_map_api.logs.url_mapped',
                                       url=url,
                                       count=link_count))
                else:
                    logger.warning(i18n.t('components.firecrawl.firecrawl_map_api.logs.no_links_found',
                                          url=url))

            logger.info(i18n.t('components.firecrawl.firecrawl_map_api.logs.mapping_completed',
                               total_links=len(combined_links),
                               urls_processed=len(urls)))

            map_result = {"success": True, "links": combined_links}
            self.status = {
                "urls_processed": len(urls),
                "total_links": len(combined_links)
            }

            return Data(data=map_result)

        except Exception as e:
            error_msg = i18n.t('components.firecrawl.firecrawl_map_api.errors.mapping_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
