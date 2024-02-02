import logging
from datetime import timedelta
from operator import attrgetter
from typing import Iterable, Optional, Sequence, TYPE_CHECKING, Any, Callable, Hashable

from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from dateutil.parser import isoparse as parse_iso_date
from flask import url_for

from .. import views
from ..models import ItemDetails, EpisodeDetails, Author, FeedOptions

from googleapiclient.discovery import build as build_google_api_client

if TYPE_CHECKING:
    import googleapiclient

    YoutubeClient = googleapiclient.discovery.Resource


def get_best_thumbnail_url(thumbnails: dict) -> str:
    return (
        thumbnails["maxres"]["url"]
        if "maxres" in thumbnails
        else thumbnails["default"]["url"]
    )


def get_channel_details(
    youtube_client: "YoutubeClient", channel_id: str
) -> Optional[ItemDetails]:
    # noinspection PyUnresolvedReferences
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
    youtube_client: "YoutubeClient", playlist_id: str
) -> Optional[ItemDetails]:
    # noinspection PyUnresolvedReferences
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


def remove_duplicates(
    objects: Sequence[Any], key_getter: Callable[[Any], Hashable]
) -> Sequence[Any]:
    unique_object_dict = {key_getter(obj): obj for obj in objects}
    return tuple(unique_object_dict.values())


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda _, playlist_details: hashkey(playlist_details.id),
)
def get_episodes_cached(
    youtube_client: "YoutubeClient", playlist_details: ItemDetails
) -> Sequence[EpisodeDetails]:
    logging.info(f"Grabbing episodes from YouTube playlist {playlist_details.id}")
    all_playlist_items = []
    # noinspection PyUnresolvedReferences
    playlist_items_endpoint = youtube_client.playlistItems()
    playlist_items_request = playlist_items_endpoint.list(
        part="snippet,status", playlistId=playlist_details.id, maxResults=50
    )
    continue_requesting_playlist_items = True
    while continue_requesting_playlist_items:
        playlist_items_response = playlist_items_request.execute()
        all_playlist_items += playlist_items_response["items"]
        playlist_items_request = playlist_items_endpoint.list_next(
            playlist_items_request, playlist_items_response
        )
        continue_requesting_playlist_items = playlist_items_request is not None
    sorted_playlist_episodes = sorted(
        map(create_episode_details, remove_unavailable_items(all_playlist_items)),
        key=attrgetter("published_at"),
    )
    return remove_duplicates(sorted_playlist_episodes, attrgetter("id"))


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda _, __, playlist_details: hashkey(playlist_details.id),
)
def get_logo_cached(
    youtube_client: "YoutubeClient",
    feed_options: FeedOptions,
    playlist_details: ItemDetails,
) -> str:
    thumbnail_path = views.get_thumbnail_path(playlist_details.id, feed_options)
    if thumbnail_path is None:
        channel_details = get_channel_details(
            youtube_client, playlist_details.author.id
        )
        return channel_details.icon_url
    else:
        if feed_options.service_config.append_auth_param_to_resource_links:
            return url_for(
                "thumbnail_view",
                thumbnail_key=playlist_details.id,
                key=feed_options.service_config.auth_key,
            )
        return url_for("thumbnail_view", thumbnail_key=playlist_details.id)


class YoutubePlaylistEpisodeFeed:
    def __init__(self, playlist_id: str, feed_options: FeedOptions):
        self.feed_options = feed_options
        self.youtube_client = build_google_api_client(
            "youtube",
            "v3",
            developerKey=self.feed_options.service_config.youtube_api_key,
            cache_discovery=False,
        )
        self.playlist_details = get_playlist_details(self.youtube_client, playlist_id)
        if self.playlist_details is None:
            raise ValueError("Playlist does not exist")

    @property
    def logo(self) -> str:
        return get_logo_cached(self.youtube_client, self.feed_options, self.playlist_details)

    @property
    def episodes(self) -> Sequence[EpisodeDetails]:
        return get_episodes_cached(self.youtube_client, self.playlist_details)

    def __iter__(self) -> Iterable[EpisodeDetails]:
        return iter(self.episodes)
