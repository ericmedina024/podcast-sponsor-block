import re

from .main import create_app
from gunicorn.glogging import Logger as GunicornLogger


class AuthKeyFilteringLogger(GunicornLogger):
    KEY_PARAM_PATTERN = re.compile(r"(key)=.+", re.IGNORECASE)
    enabled = False

    # noinspection PyProtectedMember
    def atoms(self, response, request, environ, request_time) -> dict:
        atoms: dict = super().atoms(response, request, environ, request_time)
        if not AuthKeyFilteringLogger.enabled:
            return atoms
        for atom, value in atoms.items():
            if isinstance(value, str) and "key=" in value.casefold():
                clean_value_parts = []
                split_value = value.split("&")
                for part in split_value:
                    clean_value_parts.append(AuthKeyFilteringLogger.KEY_PARAM_PATTERN.sub(r"\g<1>=redacted", part))
                atoms[atom] = "&".join(clean_value_parts)
        return atoms


__all__ = ["create_app", "AuthKeyFilteringLogger"]
