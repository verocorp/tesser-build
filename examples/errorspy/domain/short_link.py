from __future__ import annotations

from dataclasses import dataclass

from domain.values import Slug, TargetURL
from errors import conflict


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str


class ShortLink:

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = Slug(spec.slug)
        self._target = TargetURL(spec.target_url)
        self._active = True

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target(self) -> TargetURL:
        return self._target

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        if not self._active:
            raise conflict(
                "already_deactivated", f"short link {self._slug} is already deactivated"
            )
        self._active = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
