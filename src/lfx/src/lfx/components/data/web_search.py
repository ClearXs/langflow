"""Unified Web Search Component.

This component consolidates Web Search, News Search, and RSS Reader into a single
component with tabs for different search modes.
"""

import os
import re
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import i18n
import pandas as pd
import requests
from bs4 import BeautifulSoup

from lfx.custom import Component
from lfx.io import IntInput, MessageTextInput, Output, TabInput
from lfx.schema import DataFrame


class WebSearchComponent(Component):
    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"
    display_name = i18n.t("components.data.web_search.display_name")
    description = i18n.t("components.data.web_search.description")
    documentation: str = "https://docs.langflow.org/components-data#web-search"
    icon = "search"
    name = "UnifiedWebSearch"

    inputs = [
        TabInput(
            name="search_mode",
            display_name=i18n.t("components.data.web_search.search_mode.display_name"),
            options=["Web", "News", "RSS"],
            info=i18n.t("components.data.web_search.search_mode.info"),
            value="Web",
            real_time_refresh=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="query",
            display_name=i18n.t("components.data.web_search.query.display_name"),
            info=i18n.t("components.data.web_search.query.info_news"),
            tool_mode=True,
            required=True,
        ),
        MessageTextInput(
            name="hl",
            display_name=i18n.t("components.data.web_search.hl.display_name"),
            info=i18n.t("components.data.web_search.hl.info"),
            tool_mode=False,
            input_types=[],
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="gl",
            display_name=i18n.t("components.data.web_search.gl.display_name"),
            info=i18n.t("components.data.web_search.gl.info"),
            tool_mode=False,
            input_types=[],
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="ceid",
            display_name=i18n.t("components.data.web_search.ceid.display_name"),
            info=i18n.t("components.data.web_search.ceid.info"),
            tool_mode=False,
            value="US:en",
            input_types=[],
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="topic",
            display_name=i18n.t("components.data.web_search.topic.display_name"),
            info=i18n.t("components.data.web_search.topic.info"),
            tool_mode=False,
            input_types=[],
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="location",
            display_name=i18n.t("components.data.web_search.location.display_name"),
            info=i18n.t("components.data.web_search.location.info"),
            tool_mode=False,
            input_types=[],
            required=False,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t("components.data.web_search.timeout.display_name"),
            info=i18n.t("components.data.web_search.timeout.info"),
            value=5,
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="results",
            display_name=i18n.t("components.data.web_search.outputs.results.display_name"),
            method="perform_search",
        )
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        """Update input visibility based on search mode."""
        if field_name == "search_mode":
            # Update query field info based on mode
            if field_value == "RSS":
                build_config["query"]["info"] = i18n.t("components.data.web_search.query.info_rss")
                build_config["query"]["display_name"] = i18n.t("components.data.web_search.query.display_name_rss")
            elif field_value == "News":
                build_config["query"]["info"] = i18n.t("components.data.web_search.query.info_news")
                build_config["query"]["display_name"] = i18n.t("components.data.web_search.query.display_name")
            else:  # Web
                build_config["query"]["info"] = i18n.t("components.data.web_search.query.info_web")
                build_config["query"]["display_name"] = i18n.t("components.data.web_search.query.display_name")

        return build_config

    def validate_url(self, string: str) -> bool:
        """Validate URL format."""
        url_regex = re.compile(
            r"^(https?:\/\/)?" r"(www\.)?" r"([a-zA-Z0-9.-]+)" r"(\.[a-zA-Z]{2,})?" r"(:\d+)?" r"(\/[^\s]*)?$",
            re.IGNORECASE,
        )
        return bool(url_regex.match(string))

    def ensure_url(self, url: str) -> str:
        """Ensure URL has proper protocol."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        if not self.validate_url(url):
            error_message = i18n.t("components.data.web_search.errors.invalid_url", url=url)
            raise ValueError(error_message)
        return url

    def _sanitize_query(self, query: str) -> str:
        """Sanitize search query."""
        return re.sub(r'[<>"\']', "", query.strip())

    def clean_html(self, html_string: str) -> str:
        """Remove HTML tags from text."""
        return BeautifulSoup(html_string, "html.parser").get_text(separator=" ", strip=True)

    def perform_web_search(self) -> DataFrame:
        """Perform DuckDuckGo web search."""
        from bs4 import BeautifulSoup

        from lfx.utils.request_utils import get_user_agent

        query = self._sanitize_query(self.query)
        if not query:
            error_message = i18n.t("components.data.web_search.errors.empty_query")
            raise ValueError(error_message)

        headers = {"User-Agent": get_user_agent()}
        params = {"q": query, "kl": "us-en"}
        url = "https://html.duckduckgo.com/html/"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            self.status = i18n.t("components.data.web_search.errors.failed_request", error=str(e))
            return DataFrame(pd.DataFrame([{"title": "Error", "link": "", "snippet": str(e), "content": ""}]))

        if not response.text or "text/html" not in response.headers.get("content-type", "").lower():
            self.status = i18n.t("components.data.web_search.errors.no_results")
            return DataFrame(
                pd.DataFrame(
                    [
                        {
                            "title": "Error",
                            "link": "",
                            "snippet": i18n.t("components.data.web_search.errors.no_results"),
                            "content": "",
                        }
                    ]
                )
            )

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select("div.result"):
            title_tag = result.select_one("a.result__a")
            snippet_tag = result.select_one("a.result__snippet")
            if title_tag:
                raw_link = title_tag.get("href", "")
                parsed = urlparse(raw_link)
                uddg = parse_qs(parsed.query).get("uddg", [""])[0]
                decoded_link = unquote(uddg) if uddg else raw_link

                try:
                    final_url = self.ensure_url(decoded_link)
                    page = requests.get(final_url, headers=headers, timeout=self.timeout)
                    page.raise_for_status()
                    content = BeautifulSoup(page.text, "lxml").get_text(separator=" ", strip=True)
                except requests.RequestException as e:
                    final_url = decoded_link
                    content = i18n.t("components.data.web_search.errors.failed_fetch", error=str(e))

                results.append(
                    {
                        "title": title_tag.get_text(strip=True),
                        "link": final_url,
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "content": content,
                    }
                )

        return DataFrame(pd.DataFrame(results))

    def perform_news_search(self) -> DataFrame:
        """Perform Google News search."""
        query = getattr(self, "query", "")
        hl = getattr(self, "hl", "en-US") or "en-US"
        gl = getattr(self, "gl", "US") or "US"
        topic = getattr(self, "topic", None)
        location = getattr(self, "location", None)

        ceid = f"{gl}:{hl.split('-')[0]}"

        # Build RSS URL based on parameters
        if topic:
            base_url = f"https://news.google.com/rss/headlines/section/topic/{quote_plus(topic.upper())}"
            params = f"?hl={hl}&gl={gl}&ceid={ceid}"
            rss_url = base_url + params
        elif location:
            base_url = f"https://news.google.com/rss/headlines/section/geo/{quote_plus(location)}"
            params = f"?hl={hl}&gl={gl}&ceid={ceid}"
            rss_url = base_url + params
        elif query:
            base_url = "https://news.google.com/rss/search?q="
            query_encoded = quote_plus(query)
            params = f"&hl={hl}&gl={gl}&ceid={ceid}"
            rss_url = f"{base_url}{query_encoded}{params}"
        else:
            self.status = i18n.t("components.data.web_search.errors.empty_query")
            return DataFrame(
                pd.DataFrame(
                    [
                        {
                            "title": "Error",
                            "link": "",
                            "published": "",
                            "summary": i18n.t("components.data.web_search.errors.empty_query"),
                        }
                    ]
                )
            )

        try:
            response = requests.get(rss_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
        except requests.RequestException as e:
            self.status = i18n.t("components.data.web_search.errors.failed_fetch_news", error=str(e))
            return DataFrame(pd.DataFrame([{"title": "Error", "link": "", "published": "", "summary": str(e)}]))

        if not items:
            self.status = i18n.t("components.data.web_search.errors.no_articles")
            return DataFrame(
                pd.DataFrame(
                    [
                        {
                            "title": i18n.t("components.data.web_search.errors.no_articles"),
                            "link": "",
                            "published": "",
                            "summary": "",
                        }
                    ]
                )
            )

        articles = []
        for item in items:
            try:
                title = self.clean_html(item.title.text if item.title else "")
                link = item.link.text if item.link else ""
                published = item.pubDate.text if item.pubDate else ""
                summary = self.clean_html(item.description.text if item.description else "")
                articles.append({"title": title, "link": link, "published": published, "summary": summary})
            except (AttributeError, ValueError, TypeError) as e:
                self.log(i18n.t("components.data.web_search.errors.parse_article_error", error=str(e)))
                continue

        return DataFrame(pd.DataFrame(articles))

    def perform_rss_read(self) -> DataFrame:
        """Read RSS feed."""
        rss_url = getattr(self, "query", "")
        if not rss_url:
            return DataFrame(
                pd.DataFrame(
                    [
                        {
                            "title": "Error",
                            "link": "",
                            "published": "",
                            "summary": i18n.t("components.data.web_search.errors.no_rss_url"),
                        }
                    ]
                )
            )

        try:
            response = requests.get(rss_url, timeout=self.timeout)
            response.raise_for_status()
            if not response.content.strip():
                error_message = i18n.t("components.data.web_search.errors.empty_response")
                raise ValueError(error_message)

            # Validate XML
            try:
                BeautifulSoup(response.content, "xml")
            except Exception as e:
                error_message = i18n.t("components.data.web_search.errors.invalid_xml", error=str(e))
                raise ValueError(error_message) from e

            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
        except (requests.RequestException, ValueError) as e:
            self.status = i18n.t("components.data.web_search.errors.failed_fetch_rss", error=str(e))
            return DataFrame(pd.DataFrame([{"title": "Error", "link": "", "published": "", "summary": str(e)}]))

        articles = [
            {
                "title": item.title.text if item.title else "",
                "link": item.link.text if item.link else "",
                "published": item.pubDate.text if item.pubDate else "",
                "summary": item.description.text if item.description else "",
            }
            for item in items
        ]

        df_articles = pd.DataFrame(articles, columns=["title", "link", "published", "summary"])
        self.log(i18n.t("components.data.web_search.success.fetched_articles", count=len(df_articles)))
        return DataFrame(df_articles)

    def perform_search(self) -> DataFrame:
        """Main search method that routes to appropriate search function based on mode."""
        search_mode = getattr(self, "search_mode", "Web")

        if search_mode == "Web":
            return self.perform_web_search()
        if search_mode == "News":
            return self.perform_news_search()
        if search_mode == "RSS":
            return self.perform_rss_read()
        return self.perform_web_search()
