from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


@dataclass
class PodcastConfig:
    id: str
    language: Optional[str]
    description: Optional[str]
    itunes_category: Optional[str]
    explicit: Optional[bool]


@dataclass
class ServiceConfig:
    youtube_api_key: str
    auth_key: Optional[str]
    data_path: Path
    allow_query_param_auth: bool
    append_auth_param_to_resource_links: bool
    aliases: dict[str, str]
    categories_to_remove: Sequence[str]
    trusted_hosts: Sequence[str]
    podcast_configs: dict[str, PodcastConfig]


@dataclass
class Author:
    name: str
    id: str


@dataclass
class ItemDetails:
    id: str
    title: str
    description: Optional[str]
    author: Author
    icon_url: str


@dataclass
class EpisodeDetails(ItemDetails):
    published_at: datetime
