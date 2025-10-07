from typing import Any
import i18n

from langchain.tools import StructuredTool
from langchain_community.utilities.serpapi import SerpAPIWrapper
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import DictInput, IntInput, MultilineInput, SecretStrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class SerpAPISchema(BaseModel):
    """Schema for SerpAPI search parameters."""

    query: str = Field(..., description="The search query")
    params: dict[str, Any] | None = Field(
        default={
            "engine": "google",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en",
        },
        description="Additional search parameters",
    )
    max_results: int = Field(
        5, description="Maximum number of results to return")
    max_snippet_length: int = Field(
        100, description="Maximum length of each result snippet")


class SerpAPIComponent(LCToolComponent):
    display_name = i18n.t('components.tools.serp_api.display_name')
    description = i18n.t('components.tools.serp_api.description')
    name = "SerpAPI"
    icon = "SerpSearch"
    legacy = True
    replacement = ["serpapi.Serp"]

    inputs = [
        SecretStrInput(
            name="serpapi_api_key",
            display_name=i18n.t(
                'components.tools.serp_api.serpapi_api_key.display_name'),
            info=i18n.t('components.tools.serp_api.serpapi_api_key.info'),
            required=True
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.tools.serp_api.input_value.display_name'),
            info=i18n.t('components.tools.serp_api.input_value.info'),
        ),
        DictInput(
            name="search_params",
            display_name=i18n.t(
                'components.tools.serp_api.search_params.display_name'),
            info=i18n.t('components.tools.serp_api.search_params.info'),
            advanced=True,
            is_list=True
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.tools.serp_api.max_results.display_name'),
            info=i18n.t('components.tools.serp_api.max_results.info'),
            value=5,
            advanced=True
        ),
        IntInput(
            name="max_snippet_length",
            display_name=i18n.t(
                'components.tools.serp_api.max_snippet_length.display_name'),
            info=i18n.t('components.tools.serp_api.max_snippet_length.info'),
            value=100,
            advanced=True
        ),
    ]

    def _build_wrapper(self, params: dict[str, Any] | None = None) -> SerpAPIWrapper:
        """Build a SerpAPIWrapper with the provided parameters."""
        try:
            if not self.serpapi_api_key:
                error_message = i18n.t(
                    'components.tools.serp_api.errors.api_key_required')
                raise ValueError(error_message)

            params = params or {}
            if params:
                return SerpAPIWrapper(
                    serpapi_api_key=self.serpapi_api_key,
                    params=params,
                )
            return SerpAPIWrapper(serpapi_api_key=self.serpapi_api_key)
        except Exception as e:
            error_message = i18n.t(
                'components.tools.serp_api.errors.wrapper_creation_failed', error=str(e))
            raise ValueError(error_message) from e

    def build_tool(self) -> Tool:
        try:
            wrapper = self._build_wrapper(self.search_params)

            def search_func(
                query: str,
                params: dict[str, Any] | None = None,
                max_results: int = 5,
                max_snippet_length: int = 100
            ) -> list[dict[str, Any]]:
                try:
                    if not query or not query.strip():
                        warning_message = i18n.t(
                            'components.tools.serp_api.warnings.empty_query')
                        return [{"error": warning_message}]

                    local_wrapper = wrapper
                    if params:
                        local_wrapper = self._build_wrapper(params)

                    full_results = local_wrapper.results(query)
                    organic_results = full_results.get("organic_results", [])

                    if not organic_results:
                        warning_message = i18n.t(
                            'components.tools.serp_api.warnings.no_results', query=query)
                        return [{"message": warning_message, "query": query}]

                    organic_results = organic_results[:max_results]

                    limited_results = []
                    for result in organic_results:
                        limited_result = {
                            "title": result.get("title", "")[:max_snippet_length],
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", "")[:max_snippet_length],
                        }
                        limited_results.append(limited_result)

                    return limited_results

                except Exception as e:
                    error_message = i18n.t(
                        'components.tools.serp_api.errors.search_execution_failed', error=str(e))
                    logger.debug(error_message, exc_info=True)
                    raise ToolException(error_message) from e

            tool = StructuredTool.from_function(
                name="serp_search_api",
                description=i18n.t(
                    'components.tools.serp_api.tool_description'),
                func=search_func,
                args_schema=SerpAPISchema,
            )

            success_message = i18n.t(
                'components.tools.serp_api.success.tool_created')
            self.status = success_message
            return tool

        except Exception as e:
            error_message = i18n.t(
                'components.tools.serp_api.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def run_model(self) -> list[Data]:
        try:
            if not self.input_value or not self.input_value.strip():
                warning_message = i18n.t(
                    'components.tools.serp_api.warnings.empty_input')
                self.status = warning_message
                return [Data(data={"error": warning_message})]

            executing_message = i18n.t(
                'components.tools.serp_api.info.executing_search', query=self.input_value)
            self.status = executing_message

            tool = self.build_tool()
            results = tool.run({
                "query": self.input_value,
                "params": self.search_params or {},
                "max_results": self.max_results,
                "max_snippet_length": self.max_snippet_length,
            })

            if not results:
                warning_message = i18n.t(
                    'components.tools.serp_api.warnings.no_results_returned')
                self.status = warning_message
                return [Data(data={"message": warning_message, "query": self.input_value})]

            # Check if results contain error
            if len(results) == 1 and "error" in results[0]:
                error_message = results[0]["error"]
                self.status = error_message
                return [Data(data=results[0])]

            data_list = [Data(data=result, text=result.get("snippet", ""))
                         for result in results]

            success_message = i18n.t('components.tools.serp_api.success.search_completed',
                                     count=len(data_list), query=self.input_value)
            self.status = success_message
            return data_list

        except ToolException as e:
            # ToolException is already formatted with i18n message
            error_message = str(e)
            self.status = error_message
            logger.debug("Error running SerpAPI", exc_info=True)
            return [Data(data={"error": error_message}, text=error_message)]
        except Exception as e:  # noqa: BLE001
            error_message = i18n.t(
                'components.tools.serp_api.errors.execution_failed', error=str(e))
            self.status = error_message
            logger.debug("Error running SerpAPI", exc_info=True)
            return [Data(data={"error": error_message}, text=error_message)]
