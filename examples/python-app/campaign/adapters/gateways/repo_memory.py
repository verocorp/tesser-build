"""In-memory short-link store — the outbound gateway satisfying the application's
``LinkRepository`` port. ``close()`` makes it a ``lifecycle.Closeable`` so the
composition root's cleanup stack can tear it down.
"""

from __future__ import annotations

from campaign.domain.short_link import ShortLink
from campaign.domain.values import Slug
from errors import InfraError


class InMemoryLinkRepository:
    def __init__(self, *, down: bool = False) -> None:
        self._by_slug: dict[str, ShortLink] = {}
        self._down = down
        self.close_count = 0

    def save(self, link: ShortLink) -> None:
        if self._down:
            raise InfraError("campaign store unavailable")
        self._by_slug[link.slug.value] = link

    def find(self, slug: Slug) -> ShortLink | None:
        if self._down:
            raise InfraError("campaign store unavailable")
        return self._by_slug.get(slug.value)

    def all(self) -> tuple[ShortLink, ...]:
        return tuple(self._by_slug.values())

    def close(self) -> None:
        self.close_count += 1
