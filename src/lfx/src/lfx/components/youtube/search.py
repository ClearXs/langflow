import i18n
from contextlib import contextmanager

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, DropdownInput, IntInput, MessageTextInput, SecretStrInput
from lfx.schema.dataframe import DataFrame
from lfx.template.field.base import Output


class YouTubeSearchComponent(Component):
    """A component that searches YouTube videos."""

    display_name: str = i18n.t('components.youtube.search.display_name')
    description: str = i18n.t('components.youtube.search.description')
    icon: str = "YouTube"

    inputs = [
        MessageTextInput(
            name="query",
            display_name=i18n.t(
                'components.youtube.search.query.display_name'),
            info=i18n.t('components.youtube.search.query.info'),
            tool_mode=True,
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.youtube.search.api_key.display_name'),
            info=i18n.t('components.youtube.search.api_key.info'),
            required=True,
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.youtube.search.max_results.display_name'),
            value=10,
            info=i18n.t('components.youtube.search.max_results.info'),
        ),
        DropdownInput(
            name="order",
            display_name=i18n.t(
                'components.youtube.search.order.display_name'),
            options=["relevance", "date", "rating", "title", "viewCount"],
            value="relevance",
            info=i18n.t('components.youtube.search.order.info'),
        ),
        BoolInput(
            name="include_metadata",
            display_name=i18n.t(
                'components.youtube.search.include_metadata.display_name'),
            value=True,
            info=i18n.t('components.youtube.search.include_metadata.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="results",
            display_name=i18n.t('components.youtube.search.outputs.results'),
            method="search_videos"
        ),
    ]

    @contextmanager
    def youtube_client(self):
        """Context manager for YouTube API client."""
        client = build("youtube", "v3", developerKey=self.api_key)
        try:
            yield client
        finally:
            client.close()

    def search_videos(self) -> DataFrame:
        """Searches YouTube videos and returns results as DataFrame."""
        try:
            with self.youtube_client() as youtube:
                search_response = (
                    youtube.search()
                    .list(
                        q=self.query,
                        part="id,snippet",
                        maxResults=self.max_results,
                        order=self.order,
                        type="video",
                    )
                    .execute()
                )

                results = []
                for search_result in search_response.get("items", []):
                    video_id = search_result["id"]["videoId"]
                    snippet = search_result["snippet"]

                    result = {
                        "video_id": video_id,
                        "title": snippet["title"],
                        "description": snippet["description"],
                        "published_at": snippet["publishedAt"],
                        "channel_title": snippet["channelTitle"],
                        "thumbnail_url": snippet["thumbnails"]["default"]["url"],
                    }

                    if self.include_metadata:
                        # Get video details for additional metadata
                        video_response = youtube.videos().list(
                            part="statistics,contentDetails", id=video_id).execute()

                        if video_response.get("items"):
                            video_details = video_response["items"][0]
                            result.update(
                                {
                                    "view_count": int(video_details["statistics"]["viewCount"]),
                                    "like_count": int(video_details["statistics"].get("likeCount", 0)),
                                    "comment_count": int(video_details["statistics"].get("commentCount", 0)),
                                    "duration": video_details["contentDetails"]["duration"],
                                }
                            )

                    results.append(result)

                return DataFrame(pd.DataFrame(results))

        except HttpError as e:
            error_message = f"YouTube API error: {e!s}"
            return DataFrame(pd.DataFrame({"error": [error_message]}))
