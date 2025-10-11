import os
import i18n
from typing import Any

from langchain_community.utilities.searchapi import SearchApiAPIWrapper

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DictInput, DropdownInput, IntInput, MultilineInput, SecretStrInput
from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class SearchComponent(Component):
    display_name: str = i18n.t('components.searchapi.search.display_name')
    description: str = i18n.t('components.searchapi.search.description')
    documentation: str = "https://www.searchapi.io/docs/google"
    icon = "SearchAPI"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DropdownInput(
            name="engine",
            display_name=i18n.t(
                'components.searchapi.search.engine.display_name'),
            value="google",
            options=["google", "bing", "duckduckgo"]
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.searchapi.search.api_key.display_name'),
            required=True
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t(
                'components.searchapi.search.input_value.display_name'),
            tool_mode=True,
        ),
        DictInput(
            name="search_params",
            display_name=i18n.t(
                'components.searchapi.search.search_params.display_name'),
            advanced=True,
            is_list=True
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.searchapi.search.max_results.display_name'),
            value=5,
            advanced=True
        ),
        IntInput(
            name="max_snippet_length",
            display_name=i18n.t(
                'components.searchapi.search.max_snippet_length.display_name'),
            value=100,
            advanced=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.searchapi.search.outputs.dataframe.display_name'),
            name="dataframe",
            method="fetch_content_dataframe"
        ),
    ]

    def _build_wrapper(self):
        return SearchApiAPIWrapper(engine=self.engine, searchapi_api_key=self.api_key)

    def run_model(self) -> DataFrame:
        return self.fetch_content_dataframe()

    def fetch_content(self) -> list[Data]:
        wrapper = self._build_wrapper()

        def search_func(
            query: str, params: dict[str, Any] | None = None, max_results: int = 5, max_snippet_length: int = 100
        ) -> list[Data]:
            params = params or {}
            full_results = wrapper.results(query=query, **params)
            organic_results = full_results.get(
                "organic_results", [])[:max_results]

            return [
                Data(
                    text=result.get("snippet", ""),
                    data={
                        "title": result.get("title", "")[:max_snippet_length],
                        "link": result.get("link", ""),
                        "snippet": result.get("snippet", "")[:max_snippet_length],
                    },
                )
                for result in organic_results
            ]

        results = search_func(
            self.input_value,
            self.search_params or {},
            self.max_results,
            self.max_snippet_length,
        )
        self.status = results
        return results

    def fetch_content_dataframe(self) -> DataFrame:
        """Convert the search results to a DataFrame.

        Returns:
            DataFrame: A DataFrame containing the search results.
        """
        data = self.fetch_content()
        return DataFrame(data)
