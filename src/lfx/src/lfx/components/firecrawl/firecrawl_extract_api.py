import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, MultilineInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class FirecrawlExtractApi(Component):
    display_name: str = "Firecrawl Extract API"
    description: str = i18n.t(
        'components.firecrawl.firecrawl_extract_api.description')
    name = "FirecrawlExtractApi"

    documentation: str = "https://docs.firecrawl.dev/api-reference/endpoint/extract"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.api_key.display_name'),
            required=True,
            password=True,
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.api_key.info'),
        ),
        MultilineInput(
            name="urls",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.urls.display_name'),
            required=True,
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.urls.info'),
            tool_mode=True,
        ),
        MultilineInput(
            name="prompt",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.prompt.display_name'),
            required=True,
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.prompt.info'),
            tool_mode=True,
        ),
        DataInput(
            name="schema",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.schema.display_name'),
            required=False,
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.schema.info'),
        ),
        BoolInput(
            name="enable_web_search",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.enable_web_search.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.enable_web_search.info'),
        ),
        BoolInput(
            name="ignore_sitemap",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.ignore_sitemap.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.ignore_sitemap.info'),
            advanced=True,
        ),
        BoolInput(
            name="include_subdomains",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.include_subdomains.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.include_subdomains.info'),
            advanced=True,
        ),
        BoolInput(
            name="show_sources",
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.show_sources.display_name'),
            info=i18n.t(
                'components.firecrawl.firecrawl_extract_api.show_sources.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.firecrawl.firecrawl_extract_api.outputs.data.display_name'),
            name="data",
            method="extract"
        ),
    ]

    def extract(self) -> Data:
        """Extract structured data from URLs using Firecrawl API with AI-guided extraction.

        Returns:
            Data: Data object containing the extracted information.

        Raises:
            ImportError: If firecrawl-py package is not installed.
            ValueError: If API key, URLs, or prompt are missing or invalid.
        """
        try:
            from firecrawl import FirecrawlApp
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_extract_api.logs.firecrawl_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_extract_api.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        # Validate API key
        if not self.api_key:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_extract_api.errors.api_key_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate URLs
        if not self.urls:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_extract_api.errors.urls_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Split and validate URLs (handle both commas and newlines)
        logger.debug(
            i18n.t('components.firecrawl.firecrawl_extract_api.logs.parsing_urls'))
        urls = [url.strip() for url in self.urls.replace(
            "\n", ",").split(",") if url.strip()]

        if not urls:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_extract_api.errors.no_valid_urls')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.firecrawl.firecrawl_extract_api.logs.urls_parsed',
                           count=len(urls)))

        # Validate and process prompt
        if not self.prompt:
            error_msg = i18n.t(
                'components.firecrawl.firecrawl_extract_api.errors.prompt_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get the prompt text (handling both string and multiline input)
        prompt_text = self.prompt.strip()
        logger.debug(i18n.t('components.firecrawl.firecrawl_extract_api.logs.prompt_received',
                            length=len(prompt_text)))

        # Enhance the prompt to encourage comprehensive extraction
        enhanced_prompt = prompt_text
        if "schema" not in prompt_text.lower():
            enhanced_prompt = i18n.t(
                'components.firecrawl.firecrawl_extract_api.logs.enhanced_prompt',
                prompt=prompt_text
            )
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_extract_api.logs.prompt_enhanced'))

        params = {
            "prompt": enhanced_prompt,
            "enableWebSearch": self.enable_web_search,
            "ignoreSitemap": getattr(self, 'ignore_sitemap', False),
            "includeSubdomains": getattr(self, 'include_subdomains', False),
            "showSources": getattr(self, 'show_sources', False),
            "timeout": 300,
        }

        logger.debug(i18n.t('components.firecrawl.firecrawl_extract_api.logs.params_configured',
                            web_search=self.enable_web_search,
                            timeout=params["timeout"]))

        # Only add schema to params if it's provided and is a valid schema structure
        if self.schema:
            try:
                schema_added = False
                if isinstance(self.schema, dict) and "type" in self.schema:
                    params["schema"] = self.schema
                    schema_added = True
                    logger.debug(
                        i18n.t('components.firecrawl.firecrawl_extract_api.logs.schema_added_dict'))
                elif hasattr(self.schema, "dict") and "type" in self.schema.dict():
                    params["schema"] = self.schema.dict()
                    schema_added = True
                    logger.debug(
                        i18n.t('components.firecrawl.firecrawl_extract_api.logs.schema_added_object'))

                if not schema_added:
                    logger.warning(
                        i18n.t('components.firecrawl.firecrawl_extract_api.logs.schema_invalid'))

            except Exception as e:
                logger.error(i18n.t('components.firecrawl.firecrawl_extract_api.logs.schema_error',
                                    error=str(e)))

        try:
            logger.info(i18n.t('components.firecrawl.firecrawl_extract_api.logs.starting_extraction',
                               count=len(urls)))

            app = FirecrawlApp(api_key=self.api_key)
            logger.debug(
                i18n.t('components.firecrawl.firecrawl_extract_api.logs.app_initialized'))

            extract_result = app.extract(urls, params=params)

            # Log extraction results
            result_count = 0
            if isinstance(extract_result, dict):
                if "data" in extract_result:
                    result_count = len(extract_result["data"]) if isinstance(
                        extract_result["data"], list) else 1
                elif "results" in extract_result:
                    result_count = len(extract_result["results"]) if isinstance(
                        extract_result["results"], list) else 1

            logger.info(i18n.t('components.firecrawl.firecrawl_extract_api.logs.extraction_completed',
                               items=result_count))

            result_data = Data(data=extract_result)
            self.status = {"urls_processed": len(
                urls), "items_extracted": result_count}

            return result_data

        except Exception as e:
            error_msg = i18n.t('components.firecrawl.firecrawl_extract_api.errors.extraction_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
