import os
import i18n
from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class JigsawStackAIWebSearchComponent(Component):
    display_name = "AI Web Search"
    description = i18n.t('components.jigsawstack.ai_web_search.description')
    documentation = "https://jigsawstack.com/docs/api-reference/ai/search"
    icon = "JigsawStack"
    name = "JigsawStackAIWebSearch"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.api_key.display_name'),
            info=i18n.t('components.jigsawstack.ai_web_search.api_key.info'),
            required=True,
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.query.display_name'),
            info=i18n.t('components.jigsawstack.ai_web_search.query.info'),
            required=True,
            tool_mode=True,
        ),
        BoolInput(
            name="ai_overview",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.ai_overview.display_name'),
            info=i18n.t(
                'components.jigsawstack.ai_web_search.ai_overview.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="safe_mode",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.safe_mode.display_name'),
            info=i18n.t('components.jigsawstack.ai_web_search.safe_mode.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="spell_check",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.spell_check.display_name'),
            info=i18n.t(
                'components.jigsawstack.ai_web_search.spell_check.info'),
            value=True,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.max_results.display_name'),
            info=i18n.t(
                'components.jigsawstack.ai_web_search.max_results.info'),
            value=10,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.jigsawstack.ai_web_search.outputs.search_results.display_name'),
            name="search_results",
            method="search"
        ),
    ]

    def search(self) -> Data:
        """Search the web using AI.

        Returns:
            Data: Search results or error information.

        Raises:
            ImportError: If JigsawStack package is not installed.
            ValueError: If query is empty or API request fails.
        """
        logger.info(i18n.t('components.jigsawstack.ai_web_search.logs.starting_search',
                           query=self.query))

        try:
            from jigsawstack import JigsawStack, JigsawStackError
        except ImportError as e:
            error_msg = i18n.t(
                'components.jigsawstack.ai_web_search.errors.import_error')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.query or not self.query.strip():
                error_msg = i18n.t(
                    'components.jigsawstack.ai_web_search.errors.empty_query')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(
                i18n.t('components.jigsawstack.ai_web_search.logs.creating_client'))
            client = JigsawStack(api_key=self.api_key)

            # Build search parameters
            search_params = {
                "query": self.query.strip(),
                "ai_overview": self.ai_overview,
                "safe_mode": self.safe_mode,
                "spell_check": self.spell_check,
            }

            if self.max_results:
                search_params["max_results"] = self.max_results

            logger.debug(i18n.t('components.jigsawstack.ai_web_search.logs.search_parameters',
                                query=search_params["query"],
                                ai_overview=self.ai_overview,
                                safe_mode=self.safe_mode,
                                spell_check=self.spell_check,
                                max_results=self.max_results))

            # Call web search
            logger.info(
                i18n.t('components.jigsawstack.ai_web_search.logs.calling_api'))
            response = client.web.ai_search(search_params)

            if not response.get("success", False):
                error_msg = i18n.t(
                    'components.jigsawstack.ai_web_search.errors.api_request_failed')
                logger.error(error_msg)
                raise ValueError(error_msg)

            result_data = response

            # Log result statistics
            results_count = len(result_data.get("results", []))
            has_overview = "ai_overview" in result_data

            logger.info(i18n.t('components.jigsawstack.ai_web_search.logs.search_complete',
                               results_count=results_count,
                               has_overview=has_overview))

            status_msg = i18n.t('components.jigsawstack.ai_web_search.logs.search_complete_status',
                                count=results_count)
            self.status = status_msg

            return Data(data=result_data)

        except JigsawStackError as e:
            error_msg = i18n.t('components.jigsawstack.ai_web_search.errors.jigsawstack_error',
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
            error_msg = i18n.t('components.jigsawstack.ai_web_search.errors.unexpected_error',
                               error=str(e))
            logger.exception(error_msg)
            self.status = f"Error: {e!s}"
            error_data = {"error": str(e), "success": False}
            return Data(data=error_data)
