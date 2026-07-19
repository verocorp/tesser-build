from __future__ import annotations

from dataclasses import dataclass

from domain.short_link import ShortLink, ShortLinkSpec
from domain.values import DateWindow, DateWindowSpec, Slug
from errors import DomainError, conflict, not_found, wrap

_MAX_LINKS = 5


@dataclass(frozen=True)
class CampaignSpec:
    window: DateWindowSpec
    links: tuple[ShortLinkSpec, ...]


class Campaign:

    def __init__(self, id: str, spec: CampaignSpec) -> None:
        self._id = id
        self._window = DateWindow.from_spec(spec.window)
        self._links: list[ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = ShortLink(link_spec)
            except DomainError as e:
                raise wrap(
                    e, f"link {i}: {e}", field=f"links[{i}].{e.field}"
                ) from e
            self._insert(link)

    def add_link(self, spec: ShortLinkSpec) -> None:
        self._insert(ShortLink(spec))

    def deactivate_link(self, slug: Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise not_found("link_missing", f"no link {slug} in campaign {self._id}")

    @property
    def id(self) -> str:
        return self._id

    @property
    def window(self) -> DateWindow:
        return self._window

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return tuple(self._links)

    def _insert(self, link: ShortLink) -> None:
        if any(existing.slug == link.slug for existing in self._links):
            raise conflict(
                "duplicate_slug", f"slug {link.slug} already in campaign {self._id}"
            )
        if len(self._links) >= _MAX_LINKS:
            raise conflict(
                "too_many_links",
                f"campaign {self._id} is at the {_MAX_LINKS}-link cap",
            )
        self._links.append(link)
