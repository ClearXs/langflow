import os
import i18n
from pytube import Playlist  # Ensure you have pytube installed

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.template.field.base import Output


class YouTubePlaylistComponent(Component):
    display_name = i18n.t('components.youtube.playlist.display_name')
    description = i18n.t('components.youtube.playlist.description')
    icon = "YouTube"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="playlist_url",
            display_name=i18n.t(
                'components.youtube.playlist.playlist_url.display_name'),
            info=i18n.t('components.youtube.playlist.playlist_url.info'),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.youtube.playlist.outputs.video_urls'),
            name="video_urls",
            method="extract_video_urls"
        ),
    ]

    def extract_video_urls(self) -> DataFrame:
        playlist_url = self.playlist_url
        playlist = Playlist(playlist_url)
        video_urls = [video.watch_url for video in playlist.videos]

        return DataFrame([Data(data={"video_url": url}) for url in video_urls])
