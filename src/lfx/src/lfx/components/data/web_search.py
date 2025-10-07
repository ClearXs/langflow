import requests
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
from urllib.parse import urlencode, quote_plus
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, DropdownInput, BoolInput, IntInput, Output
from lfx.schema.data import Data


class WebSearchComponent(Component):
    display_name = i18n.t('components.data.web_search.display_name')
    description = i18n.t('components.data.web_search.description')
    icon = "search"
    name = "WebSearch"

    inputs = [
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.data.web_search.query.display_name'),
            info=i18n.t('components.data.web_search.query.info'),
            required=True,
            placeholder="artificial intelligence machine learning",
        ),
        MessageTextInput(
            name="api_key",
            display_name=i18n.t(
                'components.data.web_search.api_key.display_name'),
            info=i18n.t('components.data.web_search.api_key.info'),
            password=True,
            required=True,
        ),
        DropdownInput(
            name="search_engine",
            display_name=i18n.t(
                'components.data.web_search.search_engine.display_name'),
            info=i18n.t('components.data.web_search.search_engine.info'),
            options=["google", "bing", "duckduckgo", "serper", "serpapi"],
            value="google",
            real_time_refresh=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.data.web_search.max_results.display_name'),
            info=i18n.t('components.data.web_search.max_results.info'),
            value=10,
            range_spec=(1, 100),
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.data.web_search.search_type.display_name'),
            info=i18n.t('components.data.web_search.search_type.info'),
            options=["web", "images", "news", "videos", "shopping"],
            value="web",
            advanced=True,
        ),
        DropdownInput(
            name="language",
            display_name=i18n.t(
                'components.data.web_search.language.display_name'),
            info=i18n.t('components.data.web_search.language.info'),
            options=["en", "zh", "es", "fr", "de",
                     "it", "pt", "ru", "ja", "ko"],
            value="en",
            advanced=True,
        ),
        DropdownInput(
            name="country",
            display_name=i18n.t(
                'components.data.web_search.country.display_name'),
            info=i18n.t('components.data.web_search.country.info'),
            options=["us", "cn", "gb", "ca", "au",
                     "de", "fr", "jp", "kr", "in"],
            value="us",
            advanced=True,
        ),
        DropdownInput(
            name="time_range",
            display_name=i18n.t(
                'components.data.web_search.time_range.display_name'),
            info=i18n.t('components.data.web_search.time_range.info'),
            options=["any", "day", "week", "month", "year"],
            value="any",
            advanced=True,
        ),
        BoolInput(
            name="safe_search",
            display_name=i18n.t(
                'components.data.web_search.safe_search.display_name'),
            info=i18n.t('components.data.web_search.safe_search.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_snippets",
            display_name=i18n.t(
                'components.data.web_search.include_snippets.display_name'),
            info=i18n.t('components.data.web_search.include_snippets.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name=i18n.t(
                'components.data.web_search.include_metadata.display_name'),
            info=i18n.t('components.data.web_search.include_metadata.info'),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.data.web_search.timeout.display_name'),
            info=i18n.t('components.data.web_search.timeout.info'),
            value=30,
            range_spec=(5, 120),
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.web_search.text_key.display_name'),
            info=i18n.t('components.data.web_search.text_key.info'),
            value="snippet",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="search_results",
            display_name=i18n.t(
                'components.data.web_search.outputs.search_results.display_name'),
            method="perform_web_search"
        ),
        Output(
            name="search_metadata",
            display_name=i18n.t(
                'components.data.web_search.outputs.search_metadata.display_name'),
            method="get_search_metadata"
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on search engine selection."""
        if field_name == "search_engine":
            # Different search engines might have different capabilities
            if field_value in ["google", "bing"]:
                build_config["search_type"]["show"] = True
                build_config["time_range"]["show"] = True
            elif field_value == "duckduckgo":
                build_config["search_type"]["show"] = False
                build_config["time_range"]["show"] = False
            elif field_value in ["serper", "serpapi"]:
                build_config["search_type"]["show"] = True
                build_config["time_range"]["show"] = True
        return build_config

    def perform_web_search(self) -> List[Data]:
        """Perform web search and return results as Data objects."""
        try:
            if not self.query.strip():
                error_message = i18n.t(
                    'components.data.web_search.errors.empty_query')
                self.status = error_message
                raise ValueError(error_message)

            if not self.api_key.strip():
                error_message = i18n.t(
                    'components.data.web_search.errors.missing_api_key')
                self.status = error_message
                raise ValueError(error_message)

            # Perform search based on selected engine
            if self.search_engine == "google":
                results = self._search_google()
            elif self.search_engine == "bing":
                results = self._search_bing()
            elif self.search_engine == "duckduckgo":
                results = self._search_duckduckgo()
            elif self.search_engine == "serper":
                results = self._search_serper()
            elif self.search_engine == "serpapi":
                results = self._search_serpapi()
            else:
                error_message = i18n.t('components.data.web_search.errors.invalid_search_engine',
                                       engine=self.search_engine)
                self.status = error_message
                raise ValueError(error_message)

            if not results:
                self.status = i18n.t(
                    'components.data.web_search.errors.no_results')
                return []

            # Convert to Data objects
            data_results = []
            for result in results[:self.max_results]:
                data_dict = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0),
                    "search_engine": self.search_engine,
                    "query": self.query,
                }

                # Add optional fields
                if self.include_metadata:
                    data_dict.update({
                        "domain": result.get("domain", ""),
                        "published_date": result.get("published_date", ""),
                        "cached_url": result.get("cached_url", ""),
                        "similar_url": result.get("similar_url", ""),
                    })

                # Add search type specific data
                if self.search_type == "images":
                    data_dict.update({
                        "image_url": result.get("image_url", ""),
                        "thumbnail_url": result.get("thumbnail_url", ""),
                        "image_width": result.get("image_width", 0),
                        "image_height": result.get("image_height", 0),
                    })
                elif self.search_type == "news":
                    data_dict.update({
                        "source": result.get("source", ""),
                        "published_time": result.get("published_time", ""),
                        "author": result.get("author", ""),
                    })

                data_results.append(
                    Data(data=data_dict, text_key=self.text_key))

            success_message = i18n.t('components.data.web_search.success.search_completed',
                                     count=len(data_results), engine=self.search_engine)
            self.status = success_message
            return data_results

        except Exception as e:
            error_message = i18n.t(
                'components.data.web_search.errors.search_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_search_metadata(self) -> Data:
        """Get metadata about the search query and parameters."""
        try:
            metadata = {
                "query": self.query,
                "search_engine": self.search_engine,
                "search_type": self.search_type,
                "language": self.language,
                "country": self.country,
                "time_range": self.time_range,
                "max_results": self.max_results,
                "safe_search": self.safe_search,
                "timestamp": datetime.now().isoformat(),
            }

            return Data(data=metadata, text_key="query")

        except Exception as e:
            error_message = i18n.t(
                'components.data.web_search.errors.metadata_error', error=str(e))
            raise ValueError(error_message) from e

    def _search_google(self) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API."""
        url = "https://www.googleapis.com/customsearch/v1"

        params = {
            "key": self.api_key,
            "q": self.query,
            "num": min(self.max_results, 10),
            "lr": f"lang_{self.language}",
            "gl": self.country,
        }

        # Add time range filter
        if self.time_range != "any":
            date_restrict = {
                "day": "d1",
                "week": "w1",
                "month": "m1",
                "year": "y1"
            }
            params["dateRestrict"] = date_restrict.get(self.time_range)

        # Add search type
        if self.search_type == "images":
            params["searchType"] = "image"

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": idx + 1,
                "domain": item.get("displayLink", ""),
                "cached_url": item.get("cacheId", ""),
            }
            for idx, item in enumerate(items)
        ]

    def _search_bing(self) -> List[Dict[str, Any]]:
        """Search using Bing Web Search API."""
        url = "https://api.bing.microsoft.com/v7.0/search"

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": self.query,
            "count": min(self.max_results, 50),
            "mkt": f"{self.language}-{self.country}",
        }

        # Add time range filter
        if self.time_range != "any":
            freshness_map = {
                "day": "Day",
                "week": "Week",
                "month": "Month"
            }
            if self.time_range in freshness_map:
                params["freshness"] = freshness_map[self.time_range]

        response = requests.get(url, headers=headers,
                                params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        web_pages = data.get("webPages", {}).get("value", [])

        return [
            {
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "position": idx + 1,
                "domain": item.get("displayUrl", ""),
                "published_date": item.get("dateLastCrawled", ""),
            }
            for idx, item in enumerate(web_pages)
        ]

    def _search_duckduckgo(self) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo API (unofficial)."""
        # Note: This is a simplified implementation
        # Real implementation would need proper DuckDuckGo API integration
        url = "https://api.duckduckgo.com/"

        params = {
            "q": self.query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = data.get("Results", []) + data.get("RelatedTopics", [])

        search_results = []
        for idx, item in enumerate(results[:self.max_results]):
            if isinstance(item, dict) and "Text" in item:
                search_results.append({
                    "title": item.get("Text", "")[:100],
                    "url": item.get("FirstURL", ""),
                    "snippet": item.get("Text", ""),
                    "position": idx + 1,
                })

        return search_results

    def _search_serper(self) -> List[Dict[str, Any]]:
        """Search using Serper API."""
        url = "https://google.serper.dev/search"

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": self.query,
            "num": min(self.max_results, 100),
            "hl": self.language,
            "gl": self.country,
        }

        # Add time range
        if self.time_range != "any":
            time_map = {"day": "qdr:d", "week": "qdr:w",
                        "month": "qdr:m", "year": "qdr:y"}
            payload["tbs"] = time_map.get(self.time_range)

        response = requests.post(url, headers=headers,
                                 json=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        organic = data.get("organic", [])

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", idx + 1),
                "domain": item.get("domain", ""),
            }
            for idx, item in enumerate(organic)
        ]

    def _search_serpapi(self) -> List[Dict[str, Any]]:
        """Search using SerpApi."""
        url = "https://serpapi.com/search"

        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": self.query,
            "num": min(self.max_results, 100),
            "hl": self.language,
            "gl": self.country,
        }

        # Add time range
        if self.time_range != "any":
            time_map = {"day": "qdr:d", "week": "qdr:w",
                        "month": "qdr:m", "year": "qdr:y"}
            params["tbs"] = time_map.get(self.time_range)

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        organic_results = data.get("organic_results", [])

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", idx + 1),
                "domain": item.get("displayed_link", ""),
                "cached_url": item.get("cached_page_link", ""),
                "similar_url": item.get("similar_page_link", ""),
            }
            for idx, item in enumerate(organic_results)
        ]
