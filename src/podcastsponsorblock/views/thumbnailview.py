from pathlib import Path
from typing import Optional, Sequence

from flask import current_app, send_file, Response
from flask.typing import ResponseReturnValue
from flask.views import MethodView

from ..models import ServiceConfig


def compute_potential_thumbnail_stems(
    thumbnail_key: str, aliases: dict
) -> Sequence[str]:
    all_potential_thumbnail_names = [thumbnail_key]
    for alias, target in aliases.items():
        if thumbnail_key == alias:
            all_potential_thumbnail_names.append(target)
        elif thumbnail_key == target:
            all_potential_thumbnail_names.append(alias)
    return tuple(name.casefold() for name in all_potential_thumbnail_names)


def get_thumbnail_path(thumbnail_key: str, config: ServiceConfig) -> Optional[Path]:
    thumbnail_directory = config.data_path / "thumbnails"
    if not thumbnail_directory.exists() or not thumbnail_directory.is_dir():
        return None
    all_potential_thumbnail_stems = compute_potential_thumbnail_stems(
        thumbnail_key, config.aliases
    )
    for candidate_thumbnail in thumbnail_directory.iterdir():
        if (
            not candidate_thumbnail.is_file()
            or candidate_thumbnail.stem.casefold() not in all_potential_thumbnail_stems
        ):
            continue
        return candidate_thumbnail
    return None


class ThumbnailView(MethodView):
    def get(self, thumbnail_key: str) -> ResponseReturnValue:
        thumbnail_path = get_thumbnail_path(
            thumbnail_key, current_app.config["PODCAST_SERVICE_CONFIG"]
        )
        if thumbnail_path is None:
            return Response("Thumbnail not found", status=404)
        return send_file(thumbnail_path)

    def head(self, thumbnail_key: str) -> ResponseReturnValue:
        return self.get(thumbnail_key)
