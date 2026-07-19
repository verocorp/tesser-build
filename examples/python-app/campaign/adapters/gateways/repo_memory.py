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
        self._by_slug[str(link.slug)] = link

    def find(self, slug: Slug) -> ShortLink | None:
        if self._down:
            raise InfraError("campaign store unavailable")
        return self._by_slug.get(str(slug))

    def all(self) -> tuple[ShortLink, ...]:
        return tuple(self._by_slug.values())

    def close(self) -> None:
        self.close_count += 1
