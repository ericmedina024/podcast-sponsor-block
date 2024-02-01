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

from ..helpers import YoutubePlaylistEpisodeFeed, leniently_validate_youtube_id, escape_for_xml
from ..models import EpisodeDetails, ServiceConfig, PodcastConfig


class FeedAuthor(TypedDict):
    name: str


class Image(TypedDict):
    url: str
    link: str


class Link(TypedDict):
    href: str
    rel: str
    type: Optional[str]


class Enclosure(TypedDict):
    url: str
    type: str
    length: str


class Thumbnail(TypedDict):
    url: str


@dataclass
class GeneratorOptions:
    service_config: ServiceConfig
    podcast_config: Optional[PodcastConfig]
    host: str


def is_absolute(url: str) -> bool:
    return urlparse(url).netloc != ""


def add_host(url: str, generator_options: GeneratorOptions) -> str:
    host = generator_options.host
    for allowed_host in generator_options.service_config.trusted_hosts:
        # noinspection HttpUrlsUsage
        if allowed_host == f"https://{host}" or allowed_host == f"http://{host}":
            return allowed_host + url
    return url


def generate_episode_entry(
    episode: EpisodeDetails, generator_options: GeneratorOptions
) -> FeedEntry:
    feed_entry = FeedEntry()
    feed_entry.id(episode.id)
    feed_entry.title(episode.title)
    feed_entry.description(episode.description)
    feed_entry.author(FeedAuthor(name=episode.author.name))
    feed_entry.load_extension("media")
    # noinspection PyUnresolvedReferences
    feed_entry.media.thumbnail(Thumbnail(url=add_host(episode.icon_url, generator_options)))
    feed_entry.published(episode.published_at)
    if generator_options.service_config.append_auth_param_to_resource_links:
        feed_entry.enclosure(
            **Enclosure(
                url=add_host(
                    url_for(
                        "youtube_media_view", video_id=episode.id, key=generator_options.service_config.auth_key
                    ),
                    generator_options
                ),
                type="audio/mp4",
                length="0"
            )
        )
    else:
        feed_entry.link(
            Enclosure(
                url=add_host(
                    url_for("youtube_media_view", video_id=episode.id), generator_options
                ),
                type="audio/mp4",
                length="0"
            )
        )
    return feed_entry


def populate_feed_generator(
    playlist_episode_feed: YoutubePlaylistEpisodeFeed,
    generator_options: GeneratorOptions
) -> FeedGenerator:
    playlist_details = playlist_episode_feed.playlist_details
    feed_generator = FeedGenerator()
    feed_generator.title(escape_for_xml(playlist_details.title))
    feed_generator.author(FeedAuthor(name=escape_for_xml(playlist_details.author.name)))
    feed_generator.load_extension("podcast")
    youtube_playlist_url = (
        f"https://www.youtube.com/playlist?{urlencode({'list': playlist_details.id})}"
    )
    podcast_logo_url = playlist_episode_feed.logo
    if not is_absolute(podcast_logo_url):
        podcast_logo_url = add_host(podcast_logo_url, generator_options)
    feed_generator.image(
        **Image(
            url=podcast_logo_url,
            link=youtube_playlist_url,
        )
    )
    podcast_config = generator_options.podcast_config
    if podcast_config is not None:
        # noinspection PyUnresolvedReferences
        podcast_feed_generator = feed_generator.podcast
        if podcast_config.language is not None:
            feed_generator.language(escape_for_xml(podcast_config.language))
        if podcast_config.explicit is not None:
            podcast_feed_generator.itunes_explicit("yes" if podcast_config.explicit else "no")
        if podcast_config.itunes_category is not None:
            podcast_feed_generator.itunes_category(escape_for_xml(podcast_config.itunes_category))
        if podcast_feed_generator.itunes_image() is None:
            podcast_feed_generator.itunes_image("https://is1-ssl.mzstatic.com/image/thumb/Podcasts116/v4/aa/2a/c8/aa2ac8b3-8f4e-d921-7046-9a910be576b5/mza_11213880277667169347.jpg/3000x3000bb.jpg")
    feed_generator.link(Link(href=youtube_playlist_url, rel="alternate"))
    if podcast_config is not None and podcast_config.description is not None:
        feed_generator.subtitle(escape_for_xml(podcast_config.description))
    elif playlist_details.description is not None:
        feed_generator.subtitle(escape_for_xml(playlist_details.description))
    else:
        feed_generator.subtitle("No description available")
    feed_generator.id(playlist_details.id)
    if generator_options.service_config.append_auth_param_to_resource_links:
        feed_generator.link(
            Link(
                href=add_host(
                    url_for(
                        "youtube_rss_view",
                        playlist_id=playlist_details.id,
                        key=generator_options.service_config.auth_key,
                    ),
                    generator_options
                ),
                rel="self",
                type="application/rss+xml"
            )
        )
    else:
        feed_generator.link(
            Link(
                href=add_host(
                    url_for("youtube_rss_view", playlist_id=playlist_details.id),
                    generator_options
                ),
                rel="self",
                type="application/rss+xml"
            )
        )
    return feed_generator


@cached(
    TTLCache(maxsize=1024, ttl=timedelta(minutes=60).total_seconds()),
    key=lambda episode_feed, generator_options: hashkey(episode_feed.playlist_details.id, generator_options.host),
)
def generate_rss_feed(
    episode_feed: YoutubePlaylistEpisodeFeed, generator_options: GeneratorOptions
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
        try:
            episode_feed = YoutubePlaylistEpisodeFeed(
                playlist_id=playlist_id, config=service_config
            )
        except ValueError:
            return Response("Playlist does not exist", status=400)
        podcast_config = service_config.podcast_configs.get(episode_feed.playlist_details.id)
        if len(service_config.trusted_hosts) > 0:
            return Response(
                generate_rss_feed(episode_feed, GeneratorOptions(service_config, podcast_config, request.host)),
                mimetype="application/rss+xml",
            )
        else:
            return Response(
                generate_rss_feed(episode_feed, GeneratorOptions(service_config, podcast_config, "")), mimetype="application/rss+xml"
            )
