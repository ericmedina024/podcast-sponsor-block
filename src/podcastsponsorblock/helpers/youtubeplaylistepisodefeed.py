from operator import attrgetter
from typing import Iterable, Optional, Sequence

from dateutil.parser import isoparse as parse_iso_date
from flask import url_for

from .. import views
from ..models import ItemDetails, EpisodeDetails, Author, Configuration
from googleapiclient.discovery import build as build_google_api_client


def get_best_thumbnail_url(thumbnails: dict) -> str:
    return (
        thumbnails["maxres"]["url"]
        if "maxres" in thumbnails
        else thumbnails["default"]["url"]
    )


def get_channel_details(
    youtube_client: "googleapiclient.discovery.Resource", channel_id: str
) -> Optional[ItemDetails]:
    channel_request = youtube_client.channels().list(part="snippet", id=channel_id)
    channel_response = channel_request.execute()
    channel_objects = channel_response["items"]
    if len(channel_objects) == 0:
        return None
    matching_channel_object = channel_objects[0]
    channel_details = matching_channel_object["snippet"]
    return ItemDetails(
        matching_channel_object["id"],
        channel_details["title"],
        channel_details["description"],
        channel_details["title"],
        get_best_thumbnail_url(channel_details["thumbnails"]),
    )


def get_playlist_details(
    youtube_client: "googleapiclient.discovery.Resource", playlist_id: str
) -> Optional[ItemDetails]:
    playlist_request = youtube_client.playlists().list(part="snippet", id=playlist_id)
    playlist_response = playlist_request.execute()
    playlist_objects = playlist_response["items"]
    if len(playlist_objects) == 0:
        return None
    matching_playlist_object = playlist_objects[0]
    playlist_details = matching_playlist_object["snippet"]
    return ItemDetails(
        matching_playlist_object["id"],
        playlist_details["title"],
        playlist_details["description"],
        Author(playlist_details["channelTitle"], playlist_details["channelId"]),
        get_best_thumbnail_url(playlist_details["thumbnails"]),
    )


def create_episode_details(playlist_item: dict) -> "EpisodeDetails":
    video_details = playlist_item["snippet"]
    return EpisodeDetails(
        video_details["resourceId"]["videoId"],
        video_details["title"],
        video_details["description"],
        Author(video_details["channelTitle"], video_details["channelId"]),
        get_best_thumbnail_url(video_details["thumbnails"]),
        parse_iso_date(video_details["publishedAt"]),
    )


UNAVAILABLE_STATUSES = ("private", "privacyStatusUnspecified")


def remove_unavailable_items(playlist_items: Sequence[dict]) -> Sequence[dict]:
    return tuple(
        item
        for item in playlist_items
        if item["status"]["privacyStatus"] not in UNAVAILABLE_STATUSES
    )


class YoutubePlaylistEpisodeFeed:
    def __init__(self, playlist_id: str, config: Configuration):
        self.config = config
        self.youtube_client = build_google_api_client(
            "youtube",
            "v3",
            developerKey=self.config.youtube_api_key,
            cache_discovery=False,
        )
        self.playlist_details = get_playlist_details(self.youtube_client, playlist_id)
        if self.playlist_details is None:
            raise ValueError("Playlist does not exist")

    def get_logo(self) -> str:
        thumbnail_path = views.get_thumbnail_path(self.playlist_details.id, self.config)
        if thumbnail_path is None:
            channel_details = get_channel_details(
                self.youtube_client, self.playlist_details.author.id
            )
            return channel_details.icon_url
        else:
            if self.config.append_auth_param_to_resource_links:
                return url_for(
                    "thumbnail_view",
                    thumbnail_key=self.playlist_details.id,
                    key=self.config.auth_key,
                )
            return url_for("thumbnail_view", thumbnail_key=self.playlist_details.id)

    def get_episodes(self) -> Sequence[EpisodeDetails]:
        all_playlist_items = []
        playlist_items_endpoint = self.youtube_client.playlistItems()
        playlist_items_request = playlist_items_endpoint.list(
            part="snippet,status", playlistId=self.playlist_details.id, maxResults=50
        )
        continue_requesting_playlist_items = True
        while continue_requesting_playlist_items:
            playlist_items_response = playlist_items_request.execute()
            all_playlist_items += playlist_items_response["items"]
            playlist_items_request = playlist_items_endpoint.list_next(
                playlist_items_request, playlist_items_response
            )
            continue_requesting_playlist_items = playlist_items_request is not None
        return sorted(
            map(create_episode_details, remove_unavailable_items(all_playlist_items)),
            key=attrgetter("published_at"),
        )

    def __iter__(self) -> Iterable[EpisodeDetails]:
        return iter(self.get_episodes())
