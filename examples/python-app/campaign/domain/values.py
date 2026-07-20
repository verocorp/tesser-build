from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from errors import invalid
from serialization import canonical_str

_SLUG_RE = re.compile(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?")
_CAMPAIGN_ID_RE = re.compile(r"[a-f0-9]{16}")


@dataclass(frozen=True)
class CampaignID:
    _value: str

    def __post_init__(self) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(self._value):
            raise invalid("invalid_campaign_id", f"campaign id {self._value!r} must be 16 lowercase hex chars")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class Slug:
    _value: str

    def __post_init__(self) -> None:
        if not _SLUG_RE.fullmatch(self._value):
            raise invalid("invalid_slug", f"slug {self._value!r} must be 1-64 lowercase alnum/hyphen")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class TargetURL:
    _value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self._value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise invalid("invalid_target_url", f"target url {self._value!r} must be http(s) with a host")

    def __str__(self) -> str:
        return canonical_str(self._value)
