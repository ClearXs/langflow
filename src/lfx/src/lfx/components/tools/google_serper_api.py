from typing import Any
import i18n

from langchain.tools import StructuredTool
from langchain_community.utilities.google_serper import GoogleSerperAPIWrapper
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.inputs.inputs import (
    DictInput,
    DropdownInput,
    IntInput,
    MultilineInput,
    SecretStrInput,
)
from lfx.schema.data import Data


class QuerySchema(BaseModel):
    query: str = Field(..., description="The query to search for.")
    query_type: str = Field(
        "search",
        description="The type of search to perform (e.g., 'news' or 'search').",
    )
    k: int = Field(4, description="The number of results to return.")
    query_params: dict[str, Any] = Field(
        {}, description="Additional query parameters to pass to the API.")


class GoogleSerperAPIComponent(LCToolComponent):
    display_name = i18n.t('components.tools.google_serper_api.display_name')
    description = i18n.t('components.tools.google_serper_api.description')
    name = "GoogleSerperAPI"
    icon = "Google"
    legacy = True

    inputs = [
        SecretStrInput(
            name="serper_api_key",
            display_name=i18n.t(
                'components.tools.google_serper_api.serper_api_key.display_name'),
            info=i18n.t(
                'components.tools.google_serper_api.serper_api_key.info'),
            required=True
        ),
        MultilineInput(
            name="query",
            display_name=i18n.t(
                'components.tools.google_serper_api.query.display_name'),
            info=i18n.t('components.tools.google_serper_api.query.info'),
        ),
        IntInput(
            name="k",
            display_name=i18n.t(
                'components.tools.google_serper_api.k.display_name'),
            info=i18n.t('components.tools.google_serper_api.k.info'),
            value=4,
            required=True
        ),
        DropdownInput(
            name="query_type",
            display_name=i18n.t(
                'components.tools.google_serper_api.query_type.display_name'),
            info=i18n.t('components.tools.google_serper_api.query_type.info'),
            required=False,
            options=["news", "search"],
            value="search",
        ),
        DictInput(
            name="query_params",
            display_name=i18n.t(
                'components.tools.google_serper_api.query_params.display_name'),
            info=i18n.t(
                'components.tools.google_serper_api.query_params.info'),
            required=False,
            value={
                "gl": "us",
                "hl": "en",
            },
            list=True,
        ),
    ]

    def run_model(self) -> Data | list[Data]:
        try:
            if not self.query or not self.query.strip():
                warning_message = i18n.t(
                    'components.tools.google_serper_api.warnings.empty_query')
                self.status = warning_message
                return [Data(data={"error": warning_message, "results": []})]

            executing_message = i18n.t('components.tools.google_serper_api.info.searching',
                                       query=self.query, type=self.query_type, count=self.k)
            self.status = executing_message

            wrapper = self._build_wrapper(
                self.k, self.query_type, self.query_params)
            results = wrapper.results(query=self.query)

            # Adjust the extraction based on the `type`
            if self.query_type == "search":
                list_results = results.get("organic", [])
            elif self.query_type == "news":
                list_results = results.get("news", [])
            else:
                list_results = []

            if not list_results:
                warning_message = i18n.t('components.tools.google_serper_api.warnings.no_results',
                                         query=self.query, type=self.query_type)
                self.status = warning_message
                return [Data(data={"query": self.query, "type": self.query_type, "results": []})]

            data_list = []
            for result in list_results:
                result["text"] = result.pop("snippet", "")
                data_list.append(Data(data=result))

            success_message = i18n.t('components.tools.google_serper_api.success.search_completed',
                                     count=len(data_list), query=self.query, type=self.query_type)
            self.status = success_message
            return data_list

        except ImportError as e:
            error_message = i18n.t(
                'components.tools.google_serper_api.errors.import_error')
            self.status = error_message
            return [Data(data={"error": error_message, "details": str(e)})]
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_serper_api.errors.search_failed', error=str(e))
            self.status = error_message
            return [Data(data={"error": error_message, "query": self.query})]

    def build_tool(self) -> Tool:
        try:
            return StructuredTool.from_function(
                name="google_search",
                description=i18n.t(
                    'components.tools.google_serper_api.tool_description'),
                func=self._search,
                args_schema=QuerySchema,
            )
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_serper_api.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _build_wrapper(
        self,
        k: int = 5,
        query_type: str = "search",
        query_params: dict | None = None,
    ) -> GoogleSerperAPIWrapper:
        try:
            if not self.serper_api_key:
                error_message = i18n.t(
                    'components.tools.google_serper_api.errors.api_key_required')
                raise ValueError(error_message)

            wrapper_args = {
                "serper_api_key": self.serper_api_key,
                "k": k,
                "type": query_type,
            }

            # Add query_params if provided
            if query_params:
                # Merge with additional query params
                wrapper_args.update(query_params)

            # Dynamically pass parameters to the wrapper
            return GoogleSerperAPIWrapper(**wrapper_args)

        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_serper_api.errors.wrapper_creation_failed', error=str(e))
            raise ValueError(error_message) from e

    def _search(
        self,
        query: str,
        k: int = 5,
        query_type: str = "search",
        query_params: dict | None = None,
    ) -> dict:
        try:
            wrapper = self._build_wrapper(k, query_type, query_params)
            return wrapper.results(query=query)
        except Exception as e:
            error_message = i18n.t(
                'components.tools.google_serper_api.errors.search_execution_failed', error=str(e))
            raise ValueError(error_message) from e
