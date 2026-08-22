from __future__ import annotations

import tesser.domain as ts

import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, conflict, invalid, not_found


class ShortLinksSpec(ts.Spec):

    def __init__(self, links: tuple[short_link.ShortLinkSpec, ...]) -> None:
        self.links = links


class ShortLinks(ts.Entity):

    def __init__(self, spec: ShortLinksSpec) -> None:
        admitted: list[short_link.ShortLink] = []
        for index, link_spec in enumerate(spec.links):
            try:
                link = short_link.ShortLink(link_spec)
            except DomainError as e:
                raise invalid("invalid_short_link", f"invalid short link at index {index}: {e}") from e
            self._admit(admitted, link)
            admitted.append(link)
        self._links = admitted

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:
        return tuple(link._clone() for link in self._links)

    def add(self, spec: short_link.ShortLinkSpec) -> None:
        link = short_link.ShortLink(spec)
        self._admit(self._links, link)
        self._links = [*self._links, link]

    def deactivate(self, slug: values.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise not_found("link_missing", f"no short link with slug {slug}")

    def _admit(  # tesser:debt TB051
        self, links: list[short_link.ShortLink], link: short_link.ShortLink
    ) -> None:
        for existing in links:
            if existing.slug == link.slug:
                raise conflict("duplicate_slug", f"duplicate slug {link.slug} in campaign")
