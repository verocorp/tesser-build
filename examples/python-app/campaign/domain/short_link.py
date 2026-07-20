from __future__ import annotations

import copy
from dataclasses import dataclass

from campaign.domain.values import Slug, TargetURL


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str
    active: bool


class ShortLink:
    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = Slug(spec.slug)
        self._target_url = TargetURL(spec.target_url)
        self._active = spec.active

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def _clone(self) -> "ShortLink":
        return copy.copy(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
