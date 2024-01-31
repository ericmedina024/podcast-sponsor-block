import logging
from urllib.parse import urlparse, urlencode
from datetime import timedelta
from typing import TypedDict

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

from ..helpers import YoutubePlaylistEpisodeFeed, leniently_validate_youtube_id
from ..models import EpisodeDetails, Configuration


class FeedAuthor(TypedDict):
    name: str


class Image(TypedDict):
    url: str
    link: str


class Link(TypedDict):
    href: str
    rel: str


class Enclosure(Link):
    type: str


class Thumbnail(TypedDict):
    url: str


def is_absolute(url: str) -> bool:
    return urlparse(url).netloc is not ""


def add_host(url: str, host: str, config: Configuration) -> str:
    for allowed_host in config.trusted_hosts:
        # noinspection HttpUrlsUsage
        if allowed_host == f"https://{host}" or allowed_host == f"http://{host}":
            return allowed_host + url
    return url


def generate_episode_entry(
    episode: EpisodeDetails, config: Configuration, host: str
) -> FeedEntry:
    feed_entry = FeedEntry()
    feed_entry.id(episode.id)
    feed_entry.title(episode.title)
    feed_entry.description(episode.description)
    feed_entry.author(FeedAuthor(name=episode.author.name))
    feed_entry.load_extension("media")
    # noinspection PyUnresolvedReferences
    feed_entry.media.thumbnail(Thumbnail(url=add_host(episode.icon_url, host, config)))
    feed_entry.published(episode.published_at)
    if config.append_auth_param_to_resource_links:
        feed_entry.link(
            Enclosure(
                href=add_host(
                    url_for(
                        "youtube_media_view", video_id=episode.id, key=config.auth_key
                    ),
                    host,
                    config,
                ),
                rel="enclosure",
                type="audio/mp4",
            )
        )
    else:
        feed_entry.link(
            Enclosure(
                href=add_host(
                    url_for("youtube_media_view", video_id=episode.id), host, config
                ),
                rel="enclosure",
                type="audio/mp4",
            )
        )
    return feed_entry


def populate_feed_generator(
    playlist_episode_feed: YoutubePlaylistEpisodeFeed,
    config: Configuration,
    host: str,
) -> FeedGenerator:
    playlist_details = playlist_episode_feed.playlist_details
    feed_generator = FeedGenerator()
    feed_generator.title(playlist_details.title)
    feed_generator.author(FeedAuthor(name=playlist_details.author.name))
    youtube_playlist_url = (
        f"https://www.youtube.com/playlist?{urlencode({'list': playlist_details.id})}"
    )
    feed_generator.link(Link(href=youtube_playlist_url, rel="alternate"))
    podcast_logo_url = playlist_episode_feed.logo
    if not is_absolute(podcast_logo_url):
        podcast_logo_url = add_host(podcast_logo_url, host, config)
    feed_generator.image(
        **Image(
            url=podcast_logo_url,
            link=youtube_playlist_url,
        )
    )
    feed_generator.subtitle(playlist_details.description or "No description available")
    feed_generator.id(playlist_details.id)
    if config.append_auth_param_to_resource_links:
        feed_generator.link(
            Link(
                href=add_host(
                    url_for(
                        "youtube_rss_view",
                        playlist_id=playlist_details.id,
                        key=config.auth_key,
                    ),
                    host,
                    config,
                ),
                rel="self",
            )
        )
    else:
        feed_generator.link(
            Link(
                href=add_host(
                    url_for("youtube_rss_view", playlist_id=playlist_details.id),
                    host,
                    config,
                ),
                rel="self",
            )
        )
    return feed_generator


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda episode_feed, _, host: hashkey(episode_feed.playlist_details.id, host),
)
def generate_rss_feed(
    episode_feed: YoutubePlaylistEpisodeFeed, config: Configuration, host: str
) -> str:
    logging.info(
        f"Generating RSS feed for YouTube playlist {episode_feed.playlist_details.id}"
    )
    feed_generator = populate_feed_generator(episode_feed, config, host)
    for episode in episode_feed:
        feed_generator.add_entry(generate_episode_entry(episode, config, host))
    return feed_generator.rss_str()


class YoutubeRSSView(MethodView):
    def get(self, playlist_id: str) -> ResponseReturnValue:
        config: Configuration = current_app.config["PODCAST_CONFIG"]
        playlist_id = config.aliases.get(playlist_id.lower(), playlist_id)
        if not leniently_validate_youtube_id(playlist_id):
            return Response("Invalid playlist ID", status=400)
        try:
            episode_feed = YoutubePlaylistEpisodeFeed(
                playlist_id=playlist_id, config=config
            )
        except ValueError:
            return Response("Playlist does not exist", status=400)
        if len(config.trusted_hosts) > 0:
            return Response(
                generate_rss_feed(episode_feed, config, request.host),
                mimetype="text/xml",
            )
        else:
            return Response(
                generate_rss_feed(episode_feed, config, ""), mimetype="text/xml"
            )
