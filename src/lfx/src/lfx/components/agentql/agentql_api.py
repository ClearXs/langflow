import os
import i18n

from lfx.custom.custom_component.component import Component
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, MultilineInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class AgentQL(Component):
    display_name = i18n.t('components.agentql.agentql_api.display_name')
    description = i18n.t('components.agentql.agentql_api.description')
    documentation: str = "https://docs.agentql.com/"
    icon = "Globe"
    name = "AgentQL"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="url",
            display_name=i18n.t(
                'components.agentql.agentql_api.url.display_name'),
            required=True,
            info=i18n.t('components.agentql.agentql_api.url.info'),
        ),
        MultilineInput(
            name="query",
            display_name=i18n.t(
                'components.agentql.agentql_api.query.display_name'),
            required=True,
            info=i18n.t('components.agentql.agentql_api.query.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.agentql.agentql_api.api_key.display_name'),
            required=False,
            info=i18n.t('components.agentql.agentql_api.api_key.info'),
            advanced=True,
        ),
        DropdownInput(
            name="mode",
            display_name=i18n.t(
                'components.agentql.agentql_api.mode.display_name'),
            options=["standard", "fast"],
            value="standard",
            info=i18n.t('components.agentql.agentql_api.mode.info'),
            advanced=True,
        ),
        BoolInput(
            name="is_scroll_to_bottom",
            display_name=i18n.t(
                'components.agentql.agentql_api.is_scroll_to_bottom.display_name'),
            value=False,
            info=i18n.t(
                'components.agentql.agentql_api.is_scroll_to_bottom.info'),
            advanced=True,
        ),
        IntInput(
            name="wait_for_page",
            display_name=i18n.t(
                'components.agentql.agentql_api.wait_for_page.display_name'),
            value=5000,
            info=i18n.t('components.agentql.agentql_api.wait_for_page.info'),
            range_spec=RangeSpec(min=0, max=60000, step=100),
            advanced=True,
        ),
        BoolInput(
            name="is_return_markdown",
            display_name=i18n.t(
                'components.agentql.agentql_api.is_return_markdown.display_name'),
            value=False,
            info=i18n.t(
                'components.agentql.agentql_api.is_return_markdown.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.agentql.agentql_api.outputs.data.display_name'),
            name="data",
            method="extract_data",
        ),
    ]

    def extract_data(self) -> Data:
        """Extract data from a web page using AgentQL."""
        try:
            # Validate required inputs
            if not self.url or not self.url.strip():
                error_msg = i18n.t(
                    'components.agentql.agentql_api.errors.url_required')
                self.status = error_msg
                raise ValueError(error_msg)

            if not self.query or not self.query.strip():
                error_msg = i18n.t(
                    'components.agentql.agentql_api.errors.query_required')
                self.status = error_msg
                raise ValueError(error_msg)

            # Import AgentQL
            try:
                import agentql
            except ImportError as e:
                error_msg = i18n.t(
                    'components.agentql.agentql_api.errors.agentql_not_installed')
                self.status = error_msg
                raise ImportError(error_msg) from e

            self.status = i18n.t(
                'components.agentql.agentql_api.status.initializing')

            # Configure API key if provided
            api_key = getattr(self, "api_key", None)
            if api_key and api_key.strip():
                try:
                    agentql.configure(api_key=api_key)
                    logger.info(
                        i18n.t('components.agentql.agentql_api.logs.api_key_configured'))
                except Exception as e:
                    warning_msg = i18n.t('components.agentql.agentql_api.warnings.api_key_config_failed',
                                         error=str(e))
                    logger.warning(warning_msg)

            # Get configuration parameters
            mode = getattr(self, "mode", "standard")
            is_scroll_to_bottom = getattr(self, "is_scroll_to_bottom", False)
            wait_for_page = getattr(self, "wait_for_page", 5000)
            is_return_markdown = getattr(self, "is_return_markdown", False)

            self.status = i18n.t(
                'components.agentql.agentql_api.status.connecting', url=self.url)

            # Initialize browser and page
            try:
                browser = agentql.start_browser()
                page = browser.new_page()

                # Navigate to URL
                page.goto(self.url)
                logger.info(
                    i18n.t('components.agentql.agentql_api.logs.page_loaded', url=self.url))

            except Exception as e:
                error_msg = i18n.t(
                    'components.agentql.agentql_api.errors.browser_init_failed', error=str(e))
                self.status = error_msg
                raise RuntimeError(error_msg) from e

            try:
                # Wait for page to load
                if wait_for_page > 0:
                    self.status = i18n.t('components.agentql.agentql_api.status.waiting_for_page',
                                         milliseconds=wait_for_page)
                    page.wait_for_timeout(wait_for_page)

                # Scroll to bottom if enabled
                if is_scroll_to_bottom:
                    self.status = i18n.t(
                        'components.agentql.agentql_api.status.scrolling_to_bottom')
                    try:
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)")
                        # Wait for content to load after scroll
                        page.wait_for_timeout(1000)
                        logger.info(
                            i18n.t('components.agentql.agentql_api.logs.scrolled_to_bottom'))
                    except Exception as e:
                        warning_msg = i18n.t('components.agentql.agentql_api.warnings.scroll_failed',
                                             error=str(e))
                        logger.warning(warning_msg)

                # Extract data using AgentQL query
                self.status = i18n.t(
                    'components.agentql.agentql_api.status.extracting_data')

                try:
                    if mode == "fast":
                        response = page.query_data(self.query, mode="fast")
                    else:
                        response = page.query_data(self.query)

                    logger.info(
                        i18n.t('components.agentql.agentql_api.logs.data_extracted'))

                except Exception as e:
                    error_msg = i18n.t('components.agentql.agentql_api.errors.query_execution_failed',
                                       error=str(e))
                    self.status = error_msg
                    raise ValueError(error_msg) from e

                # Process response
                if response is None:
                    warning_msg = i18n.t(
                        'components.agentql.agentql_api.warnings.no_data_extracted')
                    self.status = warning_msg
                    return Data(data={"message": warning_msg})

                # Convert response to dictionary
                try:
                    if hasattr(response, "to_dict"):
                        data_dict = response.to_dict()
                    elif hasattr(response, "to_data"):
                        data_dict = response.to_data()
                    elif isinstance(response, dict):
                        data_dict = response
                    else:
                        data_dict = {"content": str(response)}

                    logger.info(
                        i18n.t('components.agentql.agentql_api.logs.response_converted'))

                except Exception as e:
                    warning_msg = i18n.t('components.agentql.agentql_api.warnings.response_conversion_failed',
                                         error=str(e))
                    logger.warning(warning_msg)
                    data_dict = {"content": str(response)}

                # Add markdown if requested
                if is_return_markdown:
                    try:
                        self.status = i18n.t(
                            'components.agentql.agentql_api.status.getting_markdown')
                        markdown_content = page.get_content(format="markdown")
                        data_dict["markdown"] = markdown_content
                        logger.info(
                            i18n.t('components.agentql.agentql_api.logs.markdown_added'))
                    except Exception as e:
                        warning_msg = i18n.t('components.agentql.agentql_api.warnings.markdown_extraction_failed',
                                             error=str(e))
                        logger.warning(warning_msg)
                        data_dict["markdown_error"] = str(e)

                # Add metadata
                data_dict["url"] = self.url
                data_dict["query"] = self.query
                data_dict["mode"] = mode

                success_msg = i18n.t('components.agentql.agentql_api.success.data_extracted',
                                     fields=len(data_dict))
                self.status = success_msg

                return Data(data=data_dict)

            finally:
                # Clean up browser resources
                try:
                    if 'browser' in locals():
                        browser.close()
                        logger.info(
                            i18n.t('components.agentql.agentql_api.logs.browser_closed'))
                except Exception as e:
                    warning_msg = i18n.t('components.agentql.agentql_api.warnings.browser_close_failed',
                                         error=str(e))
                    logger.warning(warning_msg)

        except (ValueError, ImportError, RuntimeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.agentql.agentql_api.errors.extraction_failed', error=str(e))
            self.status = error_msg
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
