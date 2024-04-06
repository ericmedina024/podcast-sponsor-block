import logging
from dataclasses import dataclass
from urllib.parse import urlparse, urlencode
from datetime import timedelta
from typing import TypedDict, Optional

from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from flask.typing import ResponseReturnValue
from flask import (
    Response,
    current_app,
    url_for,
    request,
)
from flask.views import MethodView

from ..helpers import (
    YoutubePlaylistEpisodeFeed,
    leniently_validate_youtube_id,
    escape_for_xml,
    get_itunes_artwork,
)
from ..models import EpisodeDetails, ServiceConfig, FeedOptions


class Image(TypedDict):
    url: str
    link: str


class Link(TypedDict):
    href: str
    rel: Optional[str]
    type: Optional[str]


class Enclosure(TypedDict):
    url: str
    type: str
    length: str


class Thumbnail(TypedDict):
    url: str


def is_absolute(url: str) -> bool:
    return urlparse(url).netloc != ""


def add_host(url: str, generator_options: FeedOptions) -> str:
    host = generator_options.host
    for allowed_host in generator_options.service_config.trusted_hosts:
        # noinspection HttpUrlsUsage
        if allowed_host == f"https://{host}" or allowed_host == f"http://{host}":
            return allowed_host + url
    return url


def is_valid_description(description: Optional[str]) -> bool:
    return description is not None and description != "" and not description.isspace()

def generate_episode_entry(
    episode: EpisodeDetails, generator_options: FeedOptions
) -> FeedEntry:
    feed_entry = FeedEntry()
    feed_entry.id(episode.id)
    feed_entry.title(episode.title)
    if is_valid_description(episode.description):
        feed_entry.description(episode.description)
    else:
        feed_entry.description("No description available")
    feed_entry.published(episode.published_at)
    if generator_options.service_config.append_auth_param_to_resource_links:
        feed_entry.enclosure(
            **Enclosure(
                url=add_host(
                    url_for(
                        # Apple podcasts requires the file extension
                        "youtube_media_view",
                        video_id=f"{episode.id}.m4a",
                        key=generator_options.service_config.auth_key,
                    ),
                    generator_options,
                ),
                type="audio/x-m4a",  # Apple podcasts requires this instead of audio/mp4
                length="0",
            )
        )
    else:
        feed_entry.enclosure(
            **Enclosure(
                url=add_host(
                    # Apple podcasts requires the file extension
                    url_for("youtube_media_view", video_id=f"{episode.id}.m4a"),
                    generator_options,
                ),
                type="audio/mp4",  # Apple podcasts requires this instead of audio/mp4
                length="0",
            )
        )
    return feed_entry


def populate_feed_generator(
    playlist_episode_feed: YoutubePlaylistEpisodeFeed, generator_options: FeedOptions
) -> FeedGenerator:
    playlist_details = playlist_episode_feed.playlist_details
    feed_generator = FeedGenerator()
    feed_generator.title(escape_for_xml(playlist_details.title))
    youtube_playlist_url = (
        f"https://www.youtube.com/playlist?{urlencode({'list': playlist_details.id})}"
    )
    podcast_logo_url = playlist_episode_feed.logo
    if not is_absolute(podcast_logo_url):
        podcast_logo_url = add_host(podcast_logo_url, generator_options)
    feed_generator.link(Link(href=youtube_playlist_url, rel=None, type=None))
    feed_generator.image(
        **Image(
            url=podcast_logo_url,
            link=youtube_playlist_url,
        )
    )
    feed_generator.load_extension("podcast")
    podcast_config = generator_options.podcast_config
    # noinspection PyUnresolvedReferences
    podcast_feed_generator = feed_generator.podcast
    podcast_feed_generator.itunes_author(playlist_details.author.name)
    if podcast_config is not None:
        if podcast_config.itunes_id is not None:
            try:
                itunes_artwork_url = get_itunes_artwork(podcast_config.itunes_id)
            except ValueError as exception:
                logging.error("Failed to grab iTunes artwork", exception)
            else:
                podcast_feed_generator.itunes_image(itunes_artwork_url)
        if podcast_config.language is not None:
            feed_generator.language(escape_for_xml(podcast_config.language))
        if podcast_config.explicit is not None:
            podcast_feed_generator.itunes_explicit(
                "yes" if podcast_config.explicit else "no"
            )
        if podcast_config.itunes_category is not None:
            podcast_feed_generator.itunes_category(
                escape_for_xml(podcast_config.itunes_category)
            )
    if podcast_config is not None and is_valid_description(podcast_config.description):
        feed_generator.subtitle(escape_for_xml(podcast_config.description))
    elif is_valid_description(playlist_details.description):
        feed_generator.subtitle(escape_for_xml(playlist_details.description))
    else:
        feed_generator.subtitle("No description available")
    feed_generator.id(playlist_details.id)
    return feed_generator


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda episode_feed, generator_options: hashkey(
        episode_feed.playlist_details.id, generator_options.host
    ),
)
def generate_rss_feed(
    episode_feed: YoutubePlaylistEpisodeFeed, generator_options: FeedOptions
) -> str:
    logging.info(
        f"Generating RSS feed for YouTube playlist {episode_feed.playlist_details.id}"
    )
    feed_generator = populate_feed_generator(episode_feed, generator_options)
    for episode in episode_feed:
        feed_generator.add_entry(generate_episode_entry(episode, generator_options))
    return feed_generator.rss_str()


class YoutubeRSSView(MethodView):
    def get(self, playlist_id: str) -> ResponseReturnValue:
        service_config: ServiceConfig = current_app.config["PODCAST_SERVICE_CONFIG"]
        playlist_id = service_config.aliases.get(playlist_id.lower(), playlist_id)
        if not leniently_validate_youtube_id(playlist_id):
            return Response("Invalid playlist ID", status=400)
        feed_options = FeedOptions(service_config, None, request.host)
        try:
            episode_feed = YoutubePlaylistEpisodeFeed(
                playlist_id=playlist_id, feed_options=feed_options
            )
        except ValueError:
            return Response("Playlist does not exist", status=400)
        podcast_config = service_config.podcast_configs.get(
            episode_feed.playlist_details.id
        )
        feed_options.podcast_config = podcast_config
        if len(service_config.trusted_hosts) < 1:
            feed_options.host = ""
        return Response(
            generate_rss_feed(episode_feed, feed_options),
            mimetype="application/rss+xml",
        )
