import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data

MAX_ELEMENT_PROMPTS = 5


class JigsawStackAIScraperComponent(Component):
    display_name = "AI Scraper"
    description = i18n.t('components.jigsawstack.ai_scrape.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/scrape"
    icon = "JigsawStack"
    name = "JigsawStackAIScraper"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.api_key.display_name'),
            info=i18n.t('components.jigsawstack.ai_scrape.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="url",
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.url.display_name'),
            info=i18n.t('components.jigsawstack.ai_scrape.url.info'),
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="html",
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.html.display_name'),
            info=i18n.t('components.jigsawstack.ai_scrape.html.info'),
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="element_prompts",
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.element_prompts.display_name'),
            info=i18n.t(
                'components.jigsawstack.ai_scrape.element_prompts.info'),
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="root_element_selector",
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.root_element_selector.display_name'),
            info=i18n.t(
                'components.jigsawstack.ai_scrape.root_element_selector.info'),
            required=False,
            value="main",
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.ai_scrape.outputs.scrape_results.display_name'),
            name="scrape_results",
            method="scrape"
        ),
    ]

    def scrape(self) -> Data:
        """Scrape website content using AI.

        Returns:
            Data: Scraped data or error information.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If required parameters are missing or invalid.
        """
        logger.info(
            i18n.t('components.jigsawstack.ai_scrape.logs.starting_scrape'))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.ai_scrape.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.debug(
                i18n.t('components.jigsawstack.ai_scrape.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Build request object
            scrape_params: dict = {}
            if self.url:
                scrape_params["url"] = self.url
                logger.debug(i18n.t('components.jigsawstack.ai_scrape.logs.using_url',
                                    url=self.url))
            if self.html:
                scrape_params["html"] = self.html
                logger.debug(i18n.t('components.jigsawstack.ai_scrape.logs.using_html',
                                    length=len(self.html)))

            url_value = scrape_params.get("url", "")
            html_value = scrape_params.get("html", "")
            if (not url_value or not url_value.strip()) and (not html_value or not html_value.strip()):
                error_msg = i18n.t(
                    'components.jigsawstack.ai_scrape.errors.url_or_html_required')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Process element_prompts with proper type handling
            element_prompts_list: list[str] = []
            if self.element_prompts:
                logger.debug(
                    i18n.t('components.jigsawstack.ai_scrape.logs.processing_element_prompts'))

                element_prompts_value: str | list[str] = self.element_prompts

                if isinstance(element_prompts_value, str):
                    if "," not in element_prompts_value:
                        element_prompts_list = [element_prompts_value]
                    else:
                        element_prompts_list = element_prompts_value.split(",")
                elif isinstance(element_prompts_value, list):
                    element_prompts_list = element_prompts_value
                else:
                    # Fallback for other types
                    element_prompts_list = str(
                        element_prompts_value).split(",")

                # Trim whitespace from each prompt
                element_prompts_list = [
                    prompt.strip() for prompt in element_prompts_list if prompt.strip()]

                logger.debug(i18n.t('components.jigsawstack.ai_scrape.logs.element_prompts_parsed',
                                    count=len(element_prompts_list),
                                    prompts=', '.join(element_prompts_list)))

                if len(element_prompts_list) > MAX_ELEMENT_PROMPTS:
                    error_msg = i18n.t('components.jigsawstack.ai_scrape.errors.max_elements_exceeded',
                                       max=MAX_ELEMENT_PROMPTS)
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                if len(element_prompts_list) == 0:
                    error_msg = i18n.t(
                        'components.jigsawstack.ai_scrape.errors.empty_element_prompts')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                scrape_params["element_prompts"] = element_prompts_list

            if self.root_element_selector:
                scrape_params["root_element_selector"] = self.root_element_selector
                logger.debug(i18n.t('components.jigsawstack.ai_scrape.logs.using_root_selector',
                                    selector=self.root_element_selector))

            # Call web scraping
            logger.info(
                i18n.t('components.jigsawstack.ai_scrape.logs.calling_api'))
            response = client.web.ai_scrape(scrape_params)

            if not response.get("success", False):
                error_msg = i18n.t(
                    'components.jigsawstack.ai_scrape.errors.api_request_failed')
                logger.error(error_msg)
                raise ValueError(error_msg)

            result_data = response

            status_msg = i18n.t(
                'components.jigsawstack.ai_scrape.logs.scrape_complete')
            self.status = status_msg
            logger.info(status_msg)

            return Data(data=result_data)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.ai_scrape.errors.jigsawstack_error',
                               error=str(e))
            logger.error(error_msg)
            self.status = f"Error: {e!s}"
            error_data = {"error": str(e), "success": False}
            return Data(data=error_data)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.status = f"Error: {e!s}"
            error_data = {"error": error_msg, "success": False}
            return Data(data=error_data)

        except Exception as e:
            error_msg = i18n.t('components.jigsawstack.ai_scrape.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            self.status = f"Error: {e!s}"
            error_data = {"error": str(e), "success": False}
            return Data(data=error_data)
