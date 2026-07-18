"""campaign value objects: ``Slug`` and ``TargetURL``. Private-by-convention
frozen dataclasses with a single validating constructor path (``__post_init__``),
value equality, and a display ``__str__`` that is never used for equality.

``TargetURL`` validates *well-formedness* only (http/https + a host). Whether a
well-formed destination is *allowed* is a separate concern owned by the linkpolicy
context — which is exactly why Moment 1 is a cross-context call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from errors import invalid

_SLUG_RE = re.compile(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?")


@dataclass(frozen=True)
class Slug:
    value: str

    def __post_init__(self) -> None:
        if not _SLUG_RE.fullmatch(self.value):
            raise invalid("invalid_slug", f"slug {self.value!r} must be 1-64 lowercase alnum/hyphen")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TargetURL:
    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise invalid("invalid_target_url", f"target url {self.value!r} must be http(s) with a host")

    def __str__(self) -> str:
        return self.value
