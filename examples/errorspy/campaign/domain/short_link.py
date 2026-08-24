from __future__ import annotations

import tesser.domain as ts

import campaign.domain.values as values
import tesser.errors as errors


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = values.Slug(spec.slug)
        self._target = values.TargetURL(spec.target_url)
        self._status = values.LinkStatus("active")

    @property
    def slug(self) -> values.Slug:
        return self._slug

    @property
    def target(self) -> values.TargetURL:
        return self._target

    @property
    def status(self) -> values.LinkStatus:
        return self._status

    def deactivate(self) -> None:
        if self._status == values.LinkStatus("inactive"):
            raise errors.conflict(
                "already_deactivated", f"short link {self._slug} is already deactivated"
            )
        self._status = values.LinkStatus("inactive")

    @property
    def identity(self) -> values.Slug:
        return self._slug
