from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlparse  # tessercheck:ignore TB062

import tesser.domain as ts

from errors import invalid  # tessercheck:ignore TB062
from kernel.slug import Slug as Slug
from serialization import canonical_str  # tessercheck:ignore TB062

_CAMPAIGN_ID_RE: Final[re.Pattern[str]] = re.compile(r"[a-f0-9]{16}")
_LINK_STATES: Final[frozenset[str]] = frozenset({"active", "inactive"})


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(value):
            raise invalid("invalid_campaign_id", f"campaign id {value!r} must be 16 lowercase hex chars")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class LinkStatus(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in _LINK_STATES:
            raise invalid(
                "invalid_link_status",
                f"link status {value!r} must be one of {', '.join(sorted(_LINK_STATES))}",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if any(ord(ch) < 0x20 for ch in value):
            raise invalid("invalid_target_url", "target url must not contain control characters")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise invalid("invalid_target_url", f"target url {value!r} must be http(s) with a host")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str
