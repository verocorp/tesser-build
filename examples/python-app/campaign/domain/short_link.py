from __future__ import annotations

import copy

import tesser.domain as ts

from campaign.domain.values import LinkStatus, Slug, TargetURL


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = Slug(spec.slug)
        self._target_url = TargetURL(spec.target_url)
        self._status = LinkStatus("active" if spec.active else "inactive")

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def status(self) -> LinkStatus:
        return self._status

    def deactivate(self) -> None:
        self._status = LinkStatus("inactive")

    def _clone(self) -> "ShortLink":
        return copy.copy(self)

    @property
    def identity(self) -> Slug:
        return self._slug
