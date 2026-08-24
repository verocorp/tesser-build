from __future__ import annotations

import copy

import tesser.domain as ts

import campaign.domain.short_link as short_link
import campaign.domain.values as values
import kernel.slug as kernel_slug
import tesser.errors as errors


class ShortLinksSpec(ts.Spec):

    def __init__(self, links: tuple[short_link.ShortLinkSpec, ...]) -> None:
        self.links = links


class ShortLinks(ts.Entity):

    def __init__(self, spec: ShortLinksSpec) -> None:
        admitted: list[short_link.ShortLink] = []
        for index, link_spec in enumerate(spec.links):
            try:
                link = short_link.ShortLink(link_spec)
            except errors.DomainError as e:
                raise errors.invalid("invalid_short_link", f"invalid short link at index {index}: {e}") from e
            for existing in admitted:
                if existing.slug == link.slug:
                    raise errors.conflict("duplicate_slug", f"duplicate slug {link.slug} in campaign")
            admitted.append(link)
        self._links = admitted

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:
        return tuple(copy.copy(link) for link in self._links)

    def add(self, spec: short_link.ShortLinkSpec) -> None:
        link = short_link.ShortLink(spec)
        for existing in self._links:
            if existing.slug == link.slug:
                raise errors.conflict("duplicate_slug", f"duplicate slug {link.slug} in campaign")
        self._links = [*self._links, link]

    def deactivate(self, slug: kernel_slug.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise errors.not_found("link_missing", f"no short link with slug {slug}")

    def active_target(self, slug: kernel_slug.Slug) -> values.TargetURL:
        active = values.LinkStatus(values.LinkState.ACTIVE)
        for link in self._links:
            if link.slug == slug and link.status == active:
                return link.target_url
        raise errors.not_found("link_missing", f"no active link for slug {slug}")
