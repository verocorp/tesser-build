from __future__ import annotations

import typing

import tesser.domain as ts

import campaign.domain.short_link as short_link
import campaign.domain.values as values
import tesser.errors as errors

_MAX_LINKS: typing.Final[int] = 5


class CampaignSpec(ts.Spec):

    def __init__(
        self,
        id: str,
        window: values.DateWindowSpec,
        links: tuple[short_link.ShortLinkSpec, ...],
    ) -> None:
        self.id = id
        self.window = window
        self.links = links


class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = str(values.CampaignID(spec.id))
        self._window = values.DateWindow(spec.window)
        self._links: list[short_link.ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = short_link.ShortLink(link_spec)
            except errors.DomainError as e:
                raise errors.wrap(e, f"link {i}: {e}", field=f"links[{i}].{e.field}") from e
            if any(existing.slug == link.slug for existing in self._links):
                raise errors.conflict(
                    "duplicate_slug", f"slug {link.slug} already in campaign {self._id}"
                )
            if len(self._links) >= _MAX_LINKS:
                raise errors.conflict(
                    "too_many_links",
                    f"campaign {self._id} is at the {_MAX_LINKS}-link cap",
                )
            self._links.append(link)

    def add_link(self, spec: short_link.ShortLinkSpec) -> None:
        link = short_link.ShortLink(spec)
        if any(existing.slug == link.slug for existing in self._links):
            raise errors.conflict(
                "duplicate_slug", f"slug {link.slug} already in campaign {self._id}"
            )
        if len(self._links) >= _MAX_LINKS:
            raise errors.conflict(
                "too_many_links",
                f"campaign {self._id} is at the {_MAX_LINKS}-link cap",
            )
        self._links.append(link)

    def deactivate_link(self, slug: values.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise errors.not_found("link_missing", f"no link {slug} in campaign {self._id}")

    @property
    def id(self) -> str:
        return self._id

    @property
    def window(self) -> values.DateWindow:
        return self._window

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:
        return tuple(self._links)

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
