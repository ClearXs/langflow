from typing import Any
import i18n

import httpx
from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import MultilineInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class WikidataSearchSchema(BaseModel):
    query: str = Field(..., description="The search query for Wikidata")


class WikidataAPIWrapper(BaseModel):
    """Wrapper around Wikidata API."""

    wikidata_api_url: str = "https://www.wikidata.org/w/api.php"

    def results(self, query: str) -> list[dict[str, Any]]:
        try:
            # Define request parameters for Wikidata API
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "search": query,
                "language": "en",
            }

            # Send request to Wikidata API
            response = httpx.get(self.wikidata_api_url,
                                 params=params, timeout=30.0)
            response.raise_for_status()
            response_json = response.json()

            # Extract and return search results
            return response_json.get("search", [])

        except httpx.TimeoutException as e:
            error_message = i18n.t(
                'components.tools.wikidata_api.errors.timeout')
            raise ToolException(error_message) from e
        except httpx.HTTPStatusError as e:
            error_message = i18n.t('components.tools.wikidata_api.errors.http_error',
                                   status=e.response.status_code)
            raise ToolException(error_message) from e
        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikidata_api.errors.request_failed', error=str(e))
            raise ToolException(error_message) from e

    def run(self, query: str) -> list[dict[str, Any]]:
        try:
            if not query or not query.strip():
                error_message = i18n.t(
                    'components.tools.wikidata_api.errors.empty_query')
                raise ToolException(error_message)

            results = self.results(query)
            if results:
                return results

            error_message = i18n.t(
                'components.tools.wikidata_api.errors.no_results', query=query)
            raise ToolException(error_message)

        except ToolException:
            # Re-raise ToolException as is (already has i18n message)
            raise
        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikidata_api.errors.search_failed', error=str(e))
            raise ToolException(error_message) from e


class WikidataAPIComponent(LCToolComponent):
    display_name = i18n.t('components.tools.wikidata_api.display_name')
    description = i18n.t('components.tools.wikidata_api.description')
    name = "WikidataAPI"
    icon = "Wikipedia"
    legacy = True
    replacement = ["wikipedia.WikidataComponent"]

    inputs = [
        MultilineInput(
            name="query",
            display_name=i18n.t(
                'components.tools.wikidata_api.query.display_name'),
            info=i18n.t('components.tools.wikidata_api.query.info'),
            required=True,
        ),
    ]

    def build_tool(self) -> Tool:
        try:
            wrapper = WikidataAPIWrapper()

            # Define the tool using StructuredTool and wrapper's run method
            tool = StructuredTool.from_function(
                name="wikidata_search_api",
                description=i18n.t(
                    'components.tools.wikidata_api.tool_description'),
                func=wrapper.run,
                args_schema=WikidataSearchSchema,
            )

            success_message = i18n.t(
                'components.tools.wikidata_api.success.tool_created')
            self.status = success_message

            return tool

        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikidata_api.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def run_model(self) -> list[Data]:
        try:
            if not self.query or not self.query.strip():
                warning_message = i18n.t(
                    'components.tools.wikidata_api.warnings.empty_input')
                self.status = warning_message
                return [Data(data={"error": warning_message})]

            executing_message = i18n.t(
                'components.tools.wikidata_api.info.executing_search', query=self.query)
            self.status = executing_message

            tool = self.build_tool()
            results = tool.run({"query": self.query})

            if not results:
                warning_message = i18n.t(
                    'components.tools.wikidata_api.warnings.no_results_returned')
                self.status = warning_message
                return [Data(data={"message": warning_message, "query": self.query})]

            # Transform the API response into Data objects
            data = [
                Data(
                    text=result.get("label", ""),
                    data={
                        "id": result.get("id", ""),
                        "label": result.get("label", ""),
                        "description": result.get("description", ""),
                        "url": result.get("concepturi", ""),
                        "aliases": result.get("aliases", []),
                        "match": result.get("match", {}),
                    },
                )
                for result in results
            ]

            success_message = i18n.t('components.tools.wikidata_api.success.search_completed',
                                     count=len(data), query=self.query)
            self.status = success_message

            return data

        except ToolException as e:
            # ToolException is already formatted with i18n message
            error_message = str(e)
            self.status = error_message
            logger.debug("Error running Wikidata API", exc_info=True)
            return [Data(data={"error": error_message, "query": self.query})]
        except Exception as e:
            error_message = i18n.t(
                'components.tools.wikidata_api.errors.execution_failed', error=str(e))
            self.status = error_message
            logger.debug("Error running Wikidata API", exc_info=True)
            return [Data(data={"error": error_message, "query": self.query})]
