from __future__ import annotations

import copy  # tesser:debt TB062

import tesser.domain as ts

import campaign.domain.values as values


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = values.Slug(spec.slug)
        self._target_url = values.TargetURL(spec.target_url)
        self._status = values.LinkStatus("active" if spec.active else "inactive")

    @property
    def slug(self) -> values.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def status(self) -> values.LinkStatus:
        return self._status

    def deactivate(self) -> None:
        self._status = values.LinkStatus("inactive")

    def _clone(self) -> "ShortLink":
        return copy.copy(self)

    @property
    def identity(self) -> values.Slug:
        return self._slug
