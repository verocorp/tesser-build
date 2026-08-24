from __future__ import annotations

import tesser.domain as ts

import campaign.domain.values as values
import kernel.slug as kernel_slug


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = kernel_slug.Slug(spec.slug)
        self._target_url = values.TargetURL(spec.target_url)
        self._status = values.LinkStatus(
            values.LinkState.ACTIVE if spec.active else values.LinkState.INACTIVE
        )

    @property
    def slug(self) -> kernel_slug.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def status(self) -> values.LinkStatus:
        return self._status

    def deactivate(self) -> None:
        self._status = values.LinkStatus(values.LinkState.INACTIVE)

    @property
    def identity(self) -> kernel_slug.Slug:
        return self._slug
