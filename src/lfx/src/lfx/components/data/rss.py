import feedparser
import requests
from datetime import datetime, timedelta
from typing import Any, Optional
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, BoolInput, DropdownInput, Output
from lfx.schema.data import Data


class RSSComponent(Component):
    display_name = i18n.t('components.data.rss.display_name')
    description = i18n.t('components.data.rss.description')
    icon = "rss"
    name = "RSSReaderSimple"
    legacy = True
    replacement = "data.WebSearch"

    inputs = [
        MessageTextInput(
            name="rss_url",
            display_name=i18n.t('components.data.rss.rss_url.display_name'),
            info=i18n.t('components.data.rss.rss_url.info'),
            required=True,
            placeholder="https://example.com/feed.xml",
        ),
        IntInput(
            name="max_entries",
            display_name=i18n.t(
                'components.data.rss.max_entries.display_name'),
            info=i18n.t('components.data.rss.max_entries.info'),
            value=10,
            range_spec=(1, 100),
        ),
        IntInput(
            name="days_back",
            display_name=i18n.t('components.data.rss.days_back.display_name'),
            info=i18n.t('components.data.rss.days_back.info'),
            value=7,
            range_spec=(1, 365),
            advanced=True,
        ),
        BoolInput(
            name="include_summary",
            display_name=i18n.t(
                'components.data.rss.include_summary.display_name'),
            info=i18n.t('components.data.rss.include_summary.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_content",
            display_name=i18n.t(
                'components.data.rss.include_content.display_name'),
            info=i18n.t('components.data.rss.include_content.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="parse_dates",
            display_name=i18n.t(
                'components.data.rss.parse_dates.display_name'),
            info=i18n.t('components.data.rss.parse_dates.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="sort_order",
            display_name=i18n.t('components.data.rss.sort_order.display_name'),
            info=i18n.t('components.data.rss.sort_order.info'),
            options=["newest_first", "oldest_first", "feed_order"],
            value="newest_first",
            advanced=True,
        ),
        MessageTextInput(
            name="user_agent",
            display_name=i18n.t('components.data.rss.user_agent.display_name'),
            info=i18n.t('components.data.rss.user_agent.info'),
            value="LangFlow RSS Reader 1.0",
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t('components.data.rss.timeout.display_name'),
            info=i18n.t('components.data.rss.timeout.info'),
            value=30,
            range_spec=(5, 120),
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t('components.data.rss.text_key.display_name'),
            info=i18n.t('components.data.rss.text_key.info'),
            value="summary",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="rss_entries",
            display_name=i18n.t(
                'components.data.rss.outputs.rss_entries.display_name'),
            method="fetch_rss_feed"
        ),
        Output(
            name="feed_info",
            display_name=i18n.t(
                'components.data.rss.outputs.feed_info.display_name'),
            method="get_feed_info"
        ),
    ]

    def fetch_rss_feed(self) -> list[Data]:
        try:
            if not self.rss_url.strip():
                error_message = i18n.t('components.data.rss.errors.empty_url')
                self.status = error_message
                raise ValueError(error_message)

            # Set up feedparser with custom user agent
            feedparser.USER_AGENT = self.user_agent

            # Parse the RSS feed
            feed = feedparser.parse(self.rss_url)

            if feed.bozo and hasattr(feed, 'bozo_exception'):
                warning_message = i18n.t('components.data.rss.warnings.feed_parsing_issues',
                                         error=str(feed.bozo_exception))
                self.status = warning_message

            if not feed.entries:
                error_message = i18n.t('components.data.rss.errors.no_entries')
                self.status = error_message
                return []

            # Filter entries by date if specified
            filtered_entries = self._filter_entries_by_date(feed.entries)

            # Sort entries based on sort_order
            sorted_entries = self._sort_entries(filtered_entries)

            # Limit the number of entries
            limited_entries = sorted_entries[:self.max_entries]

            # Convert entries to Data objects
            result = []
            for entry in limited_entries:
                data_dict = self._parse_entry(entry)
                result.append(Data(data=data_dict, text_key=self.text_key))

            success_message = i18n.t('components.data.rss.success.fetched_entries',
                                     count=len(result), total=len(feed.entries))
            self.status = success_message
            return result

        except Exception as e:
            error_message = i18n.t(
                'components.data.rss.errors.fetch_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_feed_info(self) -> Data:
        """Get RSS feed metadata information."""
        try:
            feedparser.USER_AGENT = self.user_agent
            feed = feedparser.parse(self.rss_url)

            feed_info = {
                "title": getattr(feed.feed, 'title', ''),
                "description": getattr(feed.feed, 'description', ''),
                "link": getattr(feed.feed, 'link', ''),
                "language": getattr(feed.feed, 'language', ''),
                "updated": getattr(feed.feed, 'updated', ''),
                "generator": getattr(feed.feed, 'generator', ''),
                "total_entries": len(feed.entries),
                "feed_url": self.rss_url,
            }

            # Add parsed date if available
            if hasattr(feed.feed, 'updated_parsed') and feed.feed.updated_parsed:
                feed_info["updated_datetime"] = datetime(
                    *feed.feed.updated_parsed[:6]).isoformat()

            return Data(data=feed_info, text_key="description")

        except Exception as e:
            error_message = i18n.t(
                'components.data.rss.errors.feed_info_error', error=str(e))
            raise ValueError(error_message) from e

    def _filter_entries_by_date(self, entries: list) -> list:
        """Filter entries based on the days_back parameter."""
        if self.days_back <= 0:
            return entries

        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        filtered_entries = []

        for entry in entries:
            entry_date = None

            # Try to get date from various possible fields
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                entry_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                entry_date = datetime(*entry.updated_parsed[:6])

            # If we have a date and it's within our range, include it
            if entry_date is None or entry_date >= cutoff_date:
                filtered_entries.append(entry)

        return filtered_entries

    def _sort_entries(self, entries: list) -> list:
        """Sort entries based on the sort_order parameter."""
        if self.sort_order == "feed_order":
            return entries

        # Sort by date
        def get_sort_date(entry):
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
            else:
                return datetime.min

        sorted_entries = sorted(entries, key=get_sort_date,
                                reverse=(self.sort_order == "newest_first"))
        return sorted_entries

    def _parse_entry(self, entry) -> dict:
        """Parse a single RSS entry into a dictionary."""
        data_dict = {
            "title": getattr(entry, 'title', ''),
            "link": getattr(entry, 'link', ''),
            "author": getattr(entry, 'author', ''),
            "published": getattr(entry, 'published', ''),
            "updated": getattr(entry, 'updated', ''),
            "id": getattr(entry, 'id', getattr(entry, 'link', '')),
        }

        # Add summary if requested
        if self.include_summary:
            data_dict["summary"] = getattr(entry, 'summary', '')

        # Add content if requested and available
        if self.include_content:
            if hasattr(entry, 'content') and entry.content:
                # content is usually a list of content objects
                content_list = []
                for content_item in entry.content:
                    content_list.append({
                        "type": getattr(content_item, 'type', 'text/html'),
                        "value": getattr(content_item, 'value', '')
                    })
                data_dict["content"] = content_list
            elif hasattr(entry, 'description'):
                data_dict["content"] = entry.description

        # Parse and add dates if requested
        if self.parse_dates:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                data_dict["published_datetime"] = datetime(
                    *entry.published_parsed[:6]).isoformat()
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                data_dict["updated_datetime"] = datetime(
                    *entry.updated_parsed[:6]).isoformat()

        # Add categories/tags if available
        if hasattr(entry, 'tags'):
            data_dict["tags"] = [
                tag.term for tag in entry.tags if hasattr(tag, 'term')]

        # Add enclosures (media files) if available
        if hasattr(entry, 'enclosures'):
            data_dict["enclosures"] = [
                {
                    "url": enc.href,
                    "type": getattr(enc, 'type', ''),
                    "length": getattr(enc, 'length', '')
                }
                for enc in entry.enclosures
            ]

        return data_dict
