from __future__ import annotations

import enum
import re
import typing
import urllib.parse as parse

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_CAMPAIGN_ID_RE: typing.Final[re.Pattern[str]] = re.compile(r"[a-f0-9]{16}")


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(value):
            raise errors.invalid("invalid_campaign_id", f"campaign id {value!r} must be 16 lowercase hex chars")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class LinkState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LinkStatus(ts.ValueObject):

    def __init__(self, value: LinkState) -> None:
        object.__setattr__(self, "_value", value.value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if any(ord(ch) < 0x20 for ch in value):
            raise errors.invalid("invalid_target_url", "target url must not contain control characters")
        parsed = parse.urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise errors.invalid("invalid_target_url", f"target url {value!r} must be http(s) with a host")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str
