import json
from collections.abc import Sequence
from typing import Any
import i18n

import requests
from langchain.agents import Tool
from langchain_core.tools import StructuredTool
from pydantic.v1 import Field, create_model

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.inputs.inputs import DropdownInput, IntInput, MessageTextInput, MultiselectInput
from lfx.io import Output
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class SearXNGToolComponent(LCToolComponent):
    search_headers: dict = {}
    display_name = i18n.t('components.tools.searxng.display_name')
    description = i18n.t('components.tools.searxng.description')
    name = "SearXNGTool"
    legacy: bool = True

    inputs = [
        MessageTextInput(
            name="url",
            display_name=i18n.t('components.tools.searxng.url.display_name'),
            info=i18n.t('components.tools.searxng.url.info'),
            value="http://localhost",
            required=True,
            refresh_button=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.tools.searxng.max_results.display_name'),
            info=i18n.t('components.tools.searxng.max_results.info'),
            value=10,
            required=True,
        ),
        MultiselectInput(
            name="categories",
            display_name=i18n.t(
                'components.tools.searxng.categories.display_name'),
            info=i18n.t('components.tools.searxng.categories.info'),
            options=[],
            value=[],
        ),
        DropdownInput(
            name="language",
            display_name=i18n.t(
                'components.tools.searxng.language.display_name'),
            info=i18n.t('components.tools.searxng.language.info'),
            options=[],
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.tools.searxng.outputs.result_tool.display_name'),
            name="result_tool",
            method="build_tool"
        ),
    ]

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None) -> dotdict:
        if field_name is None:
            return build_config

        if field_name != "url":
            return build_config

        try:
            url = f"{field_value}/config"

            response = requests.get(
                url=url, headers=self.search_headers.copy(), timeout=10)
            data = None
            if response.headers.get("Content-Encoding") == "zstd":
                data = json.loads(response.content)
            else:
                data = response.json()

            build_config["categories"]["options"] = data["categories"].copy()

            # Remove invalid categories from current selection
            for selected_category in build_config["categories"]["value"]:
                if selected_category not in build_config["categories"]["options"]:
                    build_config["categories"]["value"].remove(
                        selected_category)

            languages = list(data["locales"])
            build_config["language"]["options"] = languages.copy()

            success_message = i18n.t('components.tools.searxng.success.config_loaded',
                                     categories=len(data["categories"]),
                                     languages=len(languages))
            self.status = success_message

        except requests.RequestException as e:
            error_message = i18n.t('components.tools.searxng.errors.connection_failed',
                                   url=field_value, error=str(e))
            self.status = error_message
            logger.debug(self.status, exc_info=True)
            build_config["categories"]["options"] = [
                i18n.t('components.tools.searxng.errors.connection_error')]
        except Exception as e:  # noqa: BLE001
            error_message = i18n.t(
                'components.tools.searxng.errors.config_parsing_failed', error=str(e))
            self.status = error_message
            logger.debug(self.status, exc_info=True)
            build_config["categories"]["options"] = [
                i18n.t('components.tools.searxng.errors.failed_to_parse'),
                str(e)
            ]
        return build_config

    def build_tool(self) -> Tool:
        class SearxSearch:
            _url: str = ""
            _categories: list[str] = []
            _language: str = ""
            _headers: dict = {}
            _max_results: int = 10

            @staticmethod
            def search(query: str, categories: Sequence[str] = ()) -> list:
                try:
                    if not query or not query.strip():
                        warning_message = i18n.t(
                            'components.tools.searxng.warnings.empty_query')
                        return [{"error": warning_message}]

                    if not SearxSearch._categories and not categories:
                        error_message = i18n.t(
                            'components.tools.searxng.errors.no_categories')
                        raise ValueError(error_message)

                    all_categories = SearxSearch._categories + \
                        list(set(categories) - set(SearxSearch._categories))

                    url = f"{SearxSearch._url}/"
                    headers = SearxSearch._headers.copy()

                    response = requests.get(
                        url=url,
                        headers=headers,
                        params={
                            "q": query,
                            "categories": ",".join(all_categories),
                            "language": SearxSearch._language,
                            "format": "json",
                        },
                        timeout=10,
                    )

                    if response.status_code != 200:
                        error_message = i18n.t('components.tools.searxng.errors.search_request_failed',
                                               status=response.status_code)
                        return [{"error": error_message}]

                    response_data = response.json()
                    results = response_data.get("results", [])

                    if not results:
                        warning_message = i18n.t(
                            'components.tools.searxng.warnings.no_results', query=query)
                        return [{"message": warning_message, "query": query}]

                    num_results = min(SearxSearch._max_results, len(results))
                    return [results[i] for i in range(num_results)]

                except requests.RequestException as e:
                    error_message = i18n.t(
                        'components.tools.searxng.errors.search_connection_failed', error=str(e))
                    logger.debug("Error running SearXNG Search", exc_info=True)
                    return [{"error": error_message}]
                except Exception as e:  # noqa: BLE001
                    error_message = i18n.t(
                        'components.tools.searxng.errors.search_failed', error=str(e))
                    logger.debug("Error running SearXNG Search", exc_info=True)
                    return [{"error": error_message}]

        try:
            if not self.url:
                error_message = i18n.t(
                    'components.tools.searxng.errors.url_required')
                self.status = error_message
                raise ValueError(error_message)

            SearxSearch._url = self.url
            SearxSearch._categories = self.categories.copy()
            SearxSearch._language = self.language
            SearxSearch._headers = self.search_headers.copy()
            SearxSearch._max_results = self.max_results

            globals_ = globals()
            local = {}
            local["SearxSearch"] = SearxSearch
            globals_.update(local)

            schema_fields = {
                "query": (str, Field(..., description=i18n.t('components.tools.searxng.schema.query.description'))),
                "categories": (
                    list[str],
                    Field(
                        default=[],
                        description=i18n.t(
                            'components.tools.searxng.schema.categories.description')
                    ),
                ),
            }

            searx_search_schema = create_model(
                "SearxSearchSchema", **schema_fields)

            available_categories = ", ".join(self.categories) if self.categories else i18n.t(
                'components.tools.searxng.no_categories_configured')
            tool_description = i18n.t('components.tools.searxng.tool_description',
                                      categories=available_categories)

            success_message = i18n.t('components.tools.searxng.success.tool_created',
                                     url=self.url, max_results=self.max_results)
            self.status = success_message

            return StructuredTool.from_function(
                func=local["SearxSearch"].search,
                args_schema=searx_search_schema,
                name="searxng_search_tool",
                description=tool_description,
            )

        except Exception as e:
            error_message = i18n.t(
                'components.tools.searxng.errors.tool_creation_failed', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
