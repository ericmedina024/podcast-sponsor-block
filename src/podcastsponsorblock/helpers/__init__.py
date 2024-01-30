import re
from .youtubeplaylistepisodefeed import YoutubePlaylistEpisodeFeed

_LENIENT_YOUTUBE_ID_PATTERN = re.compile("^[A-Za-z0-9_-]{1,50}$")


def leniently_validate_youtube_id(potential_youtube_id: str) -> bool:
    return _LENIENT_YOUTUBE_ID_PATTERN.match(potential_youtube_id) is not None


__all__ = ["YoutubePlaylistEpisodeFeed", "leniently_validate_youtube_id"]
