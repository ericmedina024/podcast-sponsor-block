import re
from datetime import timedelta
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import requests
from cachetools import cached, TTLCache

from .youtubeplaylistepisodefeed import YoutubePlaylistEpisodeFeed

_LENIENT_YOUTUBE_ID_PATTERN = re.compile("^[A-Za-z0-9_-]{1,50}$")


def transform_artwork_url(artwork_url: str, new_height: int, new_width: int) -> str:
    parsed_url = urlparse(artwork_url)
    split_path = parsed_url.path.split("/")
    split_path[len(split_path) - 1] = f"{new_height}x{new_width}bb.jpg"
    new_size_path = "/".join(split_path)
    return parsed_url._replace(path=new_size_path).geturl()


@cached(cache=TTLCache(ttl=timedelta(minutes=60).total_seconds(), maxsize=1024))
def get_itunes_artwork(itunes_id: str) -> str:
    itunes_response = requests.get(
        "https://itunes.apple.com/lookup?id=", params={"id": itunes_id}
    )
    if itunes_response.status_code != 200:
        raise ValueError(f"Invalid iTunes ID: {itunes_id}")
    itunes_results = itunes_response.json().get("results", tuple())
    if len(itunes_results) != 1:
        raise ValueError(
            f"{len(itunes_results)} results found for iTunes ID: {itunes_id}"
        )
    matching_podcast = itunes_results[0]
    artwork_key = next(
        (key for key in matching_podcast.keys() if key.startswith("artworkUrl")), None
    )
    if artwork_key is None:
        raise ValueError(f"iTunes ID missing artwork: {itunes_id}")
    # even if a 3000x3000 artwork isn't available, it will return the highest available resolution. 3000x3000 is the max
    # allowed
    return transform_artwork_url(
        matching_podcast[artwork_key], new_height=3000, new_width=3000
    )


def leniently_validate_youtube_id(potential_youtube_id: str) -> bool:
    return _LENIENT_YOUTUBE_ID_PATTERN.match(potential_youtube_id) is not None


def escape_for_xml(unescaped_string: str):
    return escape(
        unescaped_string,
        entities={
            "'": "&apos;",
            '"': "&quot;",
            "©": "&#xA9;",
            "℗": "&#x2117;",
            "™": "&#x2122;",
        },
    )


__all__ = [
    "YoutubePlaylistEpisodeFeed",
    "leniently_validate_youtube_id",
    "escape_for_xml",
    "get_itunes_artwork",
]
