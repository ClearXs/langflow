import requests
from datetime import datetime, timedelta
from typing import Any, Optional
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, DropdownInput, BoolInput, Output
from lfx.schema.data import Data


class NewsSearchComponent(Component):
    display_name = i18n.t('components.data.news_search.display_name')
    description = i18n.t('components.data.news_search.description')
    icon = "newspaper"
    name = "NewsSearch"
    legacy = True
    replacement = "data.WebSearch"

    inputs = [
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.data.news_search.query.display_name'),
            info=i18n.t('components.data.news_search.query.info'),
            required=True,
        ),
        MessageTextInput(
            name="api_key",
            display_name=i18n.t(
                'components.data.news_search.api_key.display_name'),
            info=i18n.t('components.data.news_search.api_key.info'),
            password=True,
            required=True,
        ),
        DropdownInput(
            name="source",
            display_name=i18n.t(
                'components.data.news_search.source.display_name'),
            info=i18n.t('components.data.news_search.source.info'),
            options=["newsapi", "gnews", "newsdata"],
            value="newsapi",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="language",
            display_name=i18n.t(
                'components.data.news_search.language.display_name'),
            info=i18n.t('components.data.news_search.language.info'),
            options=["en", "zh", "es", "fr", "de",
                     "it", "pt", "ru", "ja", "ko"],
            value="en",
            advanced=True,
        ),
        DropdownInput(
            name="country",
            display_name=i18n.t(
                'components.data.news_search.country.display_name'),
            info=i18n.t('components.data.news_search.country.info'),
            options=["us", "cn", "gb", "ca", "au",
                     "de", "fr", "jp", "kr", "in"],
            value="us",
            advanced=True,
        ),
        DropdownInput(
            name="category",
            display_name=i18n.t(
                'components.data.news_search.category.display_name'),
            info=i18n.t('components.data.news_search.category.info'),
            options=["general", "business", "entertainment",
                     "health", "science", "sports", "technology"],
            value="general",
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.data.news_search.max_results.display_name'),
            info=i18n.t('components.data.news_search.max_results.info'),
            value=10,
            range_spec=(1, 100),
        ),
        IntInput(
            name="days_back",
            display_name=i18n.t(
                'components.data.news_search.days_back.display_name'),
            info=i18n.t('components.data.news_search.days_back.info'),
            value=7,
            range_spec=(1, 30),
            advanced=True,
        ),
        BoolInput(
            name="include_content",
            display_name=i18n.t(
                'components.data.news_search.include_content.display_name'),
            info=i18n.t('components.data.news_search.include_content.info'),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.news_search.text_key.display_name'),
            info=i18n.t('components.data.news_search.text_key.info'),
            value="content",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="news_list",
            display_name=i18n.t(
                'components.data.news_search.outputs.news_list.display_name'),
            method="search_news"
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on news source selection."""
        if field_name == "source":
            # Different sources might have different parameter requirements
            if field_value == "newsapi":
                build_config["country"]["show"] = True
                build_config["category"]["show"] = True
            elif field_value == "gnews":
                build_config["country"]["show"] = True
                build_config["category"]["show"] = False
            elif field_value == "newsdata":
                build_config["country"]["show"] = True
                build_config["category"]["show"] = True
        return build_config

    def search_news(self) -> list[Data]:
        try:
            if not self.query.strip():
                error_message = i18n.t(
                    'components.data.news_search.errors.empty_query')
                self.status = error_message
                raise ValueError(error_message)

            if not self.api_key.strip():
                error_message = i18n.t(
                    'components.data.news_search.errors.missing_api_key')
                self.status = error_message
                raise ValueError(error_message)

            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=self.days_back)

            if self.source == "newsapi":
                articles = self._search_newsapi()
            elif self.source == "gnews":
                articles = self._search_gnews()
            elif self.source == "newsdata":
                articles = self._search_newsdata()
            else:
                error_message = i18n.t(
                    'components.data.news_search.errors.invalid_source', source=self.source)
                self.status = error_message
                raise ValueError(error_message)

            if not articles:
                self.status = i18n.t(
                    'components.data.news_search.errors.no_results')
                return []

            # Convert to Data objects
            result = []
            for article in articles[:self.max_results]:
                data_dict = {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("published_at", ""),
                    "source": article.get("source", ""),
                    "author": article.get("author", ""),
                }

                if self.include_content and article.get("content"):
                    data_dict["content"] = article.get("content", "")

                # Set text field based on text_key
                text_content = ""
                if self.text_key in data_dict:
                    text_content = data_dict[self.text_key]
                else:
                    text_content = f"{article.get('title', '')} - {article.get('description', '')}"

                result.append(Data(data=data_dict, text_key=self.text_key))

            success_message = i18n.t(
                'components.data.news_search.success.found_articles', count=len(result))
            self.status = success_message
            return result

        except Exception as e:
            error_message = i18n.t(
                'components.data.news_search.errors.search_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _search_newsapi(self) -> list[dict]:
        """Search using NewsAPI."""
        url = "https://newsapi.org/v2/everything"

        from_date = (datetime.now() - timedelta(days=self.days_back)
                     ).strftime('%Y-%m-%d')

        params = {
            "q": self.query,
            "from": from_date,
            "language": self.language,
            "sortBy": "publishedAt",
            "pageSize": min(self.max_results, 100),
            "apiKey": self.api_key
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        articles = data.get("articles", [])

        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", ""),
                "author": article.get("author", ""),
            }
            for article in articles
        ]

    def _search_gnews(self) -> list[dict]:
        """Search using GNews API."""
        url = "https://gnews.io/api/v4/search"

        params = {
            "q": self.query,
            "lang": self.language,
            "country": self.country,
            "max": min(self.max_results, 100),
            "token": self.api_key
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        articles = data.get("articles", [])

        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", ""),
                "author": article.get("source", {}).get("name", ""),
            }
            for article in articles
        ]

    def _search_newsdata(self) -> list[dict]:
        """Search using NewsData API."""
        url = "https://newsdata.io/api/1/news"

        params = {
            "q": self.query,
            "language": self.language,
            "country": self.country,
            "category": self.category,
            "size": min(self.max_results, 50),
            "apikey": self.api_key
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", ""),
                "url": article.get("link", ""),
                "published_at": article.get("pubDate", ""),
                "source": article.get("source_id", ""),
                "author": article.get("creator", [""])[0] if article.get("creator") else "",
            }
            for article in results
        ]
