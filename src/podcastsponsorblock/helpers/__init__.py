import re
from xml.sax.saxutils import escape

from .youtubeplaylistepisodefeed import YoutubePlaylistEpisodeFeed

_LENIENT_YOUTUBE_ID_PATTERN = re.compile("^[A-Za-z0-9_-]{1,50}$")


def leniently_validate_youtube_id(potential_youtube_id: str) -> bool:
    return _LENIENT_YOUTUBE_ID_PATTERN.match(potential_youtube_id) is not None


def escape_for_xml(unescaped_string: str):
    return escape(unescaped_string, entities={
        "'": "&apos;",
        '"': "&quot;",
        "©": "&#xA9;",
        "℗": "&#x2117;",
        "™": "&#x2122;"
    })


__all__ = ["YoutubePlaylistEpisodeFeed", "leniently_validate_youtube_id", "escape_for_xml"]
