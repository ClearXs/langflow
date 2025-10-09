import i18n
import json
from typing import Any
from urllib.parse import urljoin

import httpx
from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel
from pydantic.v1 import Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import IntInput, MultilineInput, NestedDictInput, SecretStrInput, StrInput
from lfx.io import Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class GleanSearchAPISchema(BaseModel):
    query: str = Field(..., description="The search query")
    page_size: int = Field(
        10, description="Maximum number of results to return")
    request_options: dict[str, Any] | None = Field(
        default_factory=dict, description="Request Options")


class GleanAPIWrapper(BaseModel):
    """Wrapper around Glean API."""

    glean_api_url: str
    glean_access_token: str
    act_as: str = "langflow-component@datastax.com"  # TODO: Detect this

    def _prepare_request(
        self,
        query: str,
        page_size: int = 10,
        request_options: dict[str, Any] | None = None,
    ) -> dict:
        """Prepare the HTTP request for Glean API."""
        # Ensure there's a trailing slash
        url = self.glean_api_url
        if not url.endswith("/"):
            url += "/"

        logger.debug(i18n.t('components.glean.glean_search_api.logs.preparing_request',
                            url=url,
                            query=query[:100] + ("..." if len(query) > 100 else "")))

        return {
            "url": urljoin(url, "search"),
            "headers": {
                "Authorization": f"Bearer {self.glean_access_token}",
                "X-Scio-ActAs": self.act_as,
            },
            "payload": {
                "query": query,
                "pageSize": page_size,
                "requestOptions": request_options,
            },
        }

    def results(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Get search results from Glean API."""
        logger.info(
            i18n.t('components.glean.glean_search_api.logs.fetching_results'))

        results = self._search_api_results(query, **kwargs)

        if len(results) == 0:
            msg = i18n.t('components.glean.glean_search_api.errors.no_results')
            logger.warning(msg)
            raise AssertionError(msg)

        logger.info(i18n.t('components.glean.glean_search_api.logs.results_fetched',
                           count=len(results)))
        return results

    def run(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Execute search and process results."""
        try:
            logger.info(i18n.t('components.glean.glean_search_api.logs.executing_search',
                               query=query[:100] + ("..." if len(query) > 100 else "")))

            results = self.results(query, **kwargs)

            processed_results = []
            for result in results:
                if "title" in result:
                    result["snippets"] = result.get(
                        "snippets", [{"snippet": {"text": result["title"]}}])
                    if "text" not in result["snippets"][0]:
                        result["snippets"][0]["text"] = result["title"]

                processed_results.append(result)

            logger.info(i18n.t('components.glean.glean_search_api.logs.results_processed',
                               count=len(processed_results)))

        except Exception as e:
            error_message = i18n.t('components.glean.glean_search_api.errors.search_failed',
                                   error=str(e))
            logger.exception(error_message)
            raise ToolException(error_message) from e

        return processed_results

    def _search_api_results(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Call Glean Search API and return results."""
        request_details = self._prepare_request(query, **kwargs)

        try:
            logger.debug(i18n.t('components.glean.glean_search_api.logs.sending_request',
                                url=request_details["url"]))

            response = httpx.post(
                request_details["url"],
                json=request_details["payload"],
                headers=request_details["headers"],
            )

            response.raise_for_status()
            logger.debug(i18n.t('components.glean.glean_search_api.logs.request_successful',
                                status=response.status_code))

            response_json = response.json()
            results = response_json.get("results", [])

            logger.debug(i18n.t('components.glean.glean_search_api.logs.response_parsed',
                                count=len(results)))

            return results

        except httpx.HTTPStatusError as e:
            error_msg = i18n.t('components.glean.glean_search_api.errors.http_error',
                               status=e.response.status_code,
                               error=str(e))
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = i18n.t('components.glean.glean_search_api.errors.request_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise

    @staticmethod
    def _result_as_string(result: dict) -> str:
        """Convert result dictionary to formatted JSON string."""
        return json.dumps(result, indent=4)


class GleanSearchAPIComponent(LCToolComponent):
    display_name: str = "Glean Search API"
    description: str = i18n.t('components.glean.glean_search_api.description')
    documentation: str = "https://docs.langflow.org/Components/components-tools#glean-search-api"
    icon: str = "Glean"

    outputs = [
        Output(
            display_name=i18n.t(
                'components.glean.glean_search_api.outputs.dataframe.display_name'),
            name="dataframe",
            method="fetch_content_dataframe"
        ),
    ]

    inputs = [
        StrInput(
            name="glean_api_url",
            display_name=i18n.t(
                'components.glean.glean_search_api.glean_api_url.display_name'),
            required=True,
            info=i18n.t(
                'components.glean.glean_search_api.glean_api_url.info'),
        ),
        SecretStrInput(
            name="glean_access_token",
            display_name=i18n.t(
                'components.glean.glean_search_api.glean_access_token.display_name'),
            required=True,
            info=i18n.t(
                'components.glean.glean_search_api.glean_access_token.info'),
        ),
        MultilineInput(
            name="query",
            display_name=i18n.t(
                'components.glean.glean_search_api.query.display_name'),
            required=True,
            tool_mode=True,
            info=i18n.t('components.glean.glean_search_api.query.info'),
        ),
        IntInput(
            name="page_size",
            display_name=i18n.t(
                'components.glean.glean_search_api.page_size.display_name'),
            value=10,
            info=i18n.t('components.glean.glean_search_api.page_size.info'),
        ),
        NestedDictInput(
            name="request_options",
            display_name=i18n.t(
                'components.glean.glean_search_api.request_options.display_name'),
            required=False,
            info=i18n.t(
                'components.glean.glean_search_api.request_options.info'),
        ),
    ]

    def build_tool(self) -> Tool:
        """Build the Glean Search tool for LangChain."""
        logger.info(
            i18n.t('components.glean.glean_search_api.logs.building_tool'))

        wrapper = self._build_wrapper(
            glean_api_url=self.glean_api_url,
            glean_access_token=self.glean_access_token,
        )

        tool = StructuredTool.from_function(
            name="glean_search_api",
            description=i18n.t(
                'components.glean.glean_search_api.tool_description'),
            func=wrapper.run,
            args_schema=GleanSearchAPISchema,
        )

        status_msg = i18n.t(
            'components.glean.glean_search_api.logs.tool_built')
        self.status = status_msg
        logger.info(status_msg)

        return tool

    def run_model(self) -> DataFrame:
        """Run the model and return DataFrame."""
        logger.info(
            i18n.t('components.glean.glean_search_api.logs.running_model'))
        return self.fetch_content_dataframe()

    def fetch_content(self) -> list[Data]:
        """Fetch content from Glean Search API."""
        logger.info(
            i18n.t('components.glean.glean_search_api.logs.fetching_content'))

        tool = self.build_tool()

        try:
            results = tool.run(
                {
                    "query": self.query,
                    "page_size": self.page_size,
                    "request_options": self.request_options,
                }
            )

            # Build the data
            data = [Data(data=result, text=result["snippets"][0]["text"])
                    for result in results]

            logger.info(i18n.t('components.glean.glean_search_api.logs.content_fetched',
                               count=len(data)))

            self.status = data  # type: ignore[assignment]
            return data

        except Exception as e:
            error_msg = i18n.t('components.glean.glean_search_api.errors.fetch_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise

    def _build_wrapper(
        self,
        glean_api_url: str,
        glean_access_token: str,
    ):
        """Build the Glean API wrapper."""
        logger.debug(
            i18n.t('components.glean.glean_search_api.logs.building_wrapper'))

        return GleanAPIWrapper(
            glean_api_url=glean_api_url,
            glean_access_token=glean_access_token,
        )

    def fetch_content_dataframe(self) -> DataFrame:
        """Convert the Glean search results to a DataFrame.

        Returns:
            DataFrame: A DataFrame containing the search results.
        """
        logger.info(
            i18n.t('components.glean.glean_search_api.logs.converting_to_dataframe'))

        data = self.fetch_content()
        df = DataFrame(data)

        logger.info(i18n.t('components.glean.glean_search_api.logs.dataframe_created',
                           rows=len(df)))

        return df
