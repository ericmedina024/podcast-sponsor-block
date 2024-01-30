import logging
import urllib.parse
from datetime import timedelta
from typing import TypedDict

from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from flask.typing import ResponseReturnValue
from flask import Response, current_app, url_for
from flask.views import MethodView

from ..helpers import YoutubePlaylistEpisodeFeed, leniently_validate_youtube_id
from ..models import EpisodeDetails, Configuration


class FeedAuthor(TypedDict):
    name: str


class Link(TypedDict):
    href: str
    rel: str


class Enclosure(Link):
    type: str


class Thumbnail(TypedDict):
    url: str


def generate_episode_entry(episode: EpisodeDetails, config: Configuration) -> FeedEntry:
    feed_entry = FeedEntry()
    feed_entry.id(episode.id)
    feed_entry.title(episode.title)
    feed_entry.description(episode.description)
    feed_entry.author(FeedAuthor(name=episode.author.name))
    feed_entry.load_extension("media")
    # noinspection PyUnresolvedReferences
    feed_entry.media.thumbnail(Thumbnail(url=episode.icon_url))
    feed_entry.published(episode.published_at)
    if config.append_auth_param_to_resource_links:
        feed_entry.link(
            Enclosure(
                href=url_for(
                    "youtube_media_view", video_id=episode.id, key=config.auth_key
                ),
                rel="enclosure",
                type="audio/mp4",
            )
        )
    else:
        feed_entry.link(
            Enclosure(
                href=url_for("youtube_media_view", video_id=episode.id),
                rel="enclosure",
                type="audio/mp4",
            )
        )
    return feed_entry


def populate_feed_generator(
    playlist_episode_feed: YoutubePlaylistEpisodeFeed, config: Configuration
) -> FeedGenerator:
    playlist_details = playlist_episode_feed.playlist_details
    feed_generator = FeedGenerator()
    feed_generator.title(playlist_details.title)
    feed_generator.author(FeedAuthor(name=playlist_details.author.name))
    youtube_playlist_url = f"https://www.youtube.com/playlist?{urllib.parse.urlencode({'list': playlist_details.id})}"
    feed_generator.link(Link(href=youtube_playlist_url, rel="alternate"))
    feed_generator.logo(playlist_episode_feed.get_logo())
    feed_generator.subtitle(playlist_details.description or "No description available")
    feed_generator.id(playlist_details.id)
    if config.append_auth_param_to_resource_links:
        feed_generator.link(
            Link(
                href=url_for(
                    "youtube_rss_view",
                    playlist_id=playlist_details.id,
                    key=config.auth_key,
                ),
                rel="self",
            )
        )
    else:
        feed_generator.link(
            Link(
                href=url_for("youtube_rss_view", playlist_id=playlist_details.id),
                rel="self",
            )
        )
    return feed_generator


def generate_rss_feed(
    episode_feed: YoutubePlaylistEpisodeFeed, config: Configuration
) -> str:
    feed_generator = populate_feed_generator(episode_feed, config)
    for episode in episode_feed:
        feed_generator.add_entry(generate_episode_entry(episode, config))
    return feed_generator.rss_str()


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda playlist_id, _: hashkey(playlist_id),
)
def generate_response(playlist_id: str, config: Configuration) -> ResponseReturnValue:
    playlist_id = config.aliases.get(playlist_id.lower(), playlist_id)
    if not leniently_validate_youtube_id(playlist_id):
        return Response("Invalid playlist ID", status=400)
    try:
        episode_feed = YoutubePlaylistEpisodeFeed(
            playlist_id=playlist_id, config=config
        )
    except ValueError:
        return Response("Playlist does not exist", status=400)
    logging.info(
        f"Generating RSS feed for YouTube playlist {episode_feed.playlist_details.id}"
    )
    return Response(generate_rss_feed(episode_feed, config), mimetype="text/xml")


class YoutubeRSSView(MethodView):
    def get(self, playlist_id: str) -> ResponseReturnValue:
        # noinspection PyCallingNonCallable
        return generate_response(playlist_id, current_app.config["PODCAST_CONFIG"])
