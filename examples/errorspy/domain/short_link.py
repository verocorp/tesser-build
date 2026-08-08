from __future__ import annotations

from dataclasses import dataclass

from domain.values import LinkStatus, Slug, TargetURL, Truth
from errors import conflict


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str


class ShortLink:

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = Slug(spec.slug)
        self._target = TargetURL(spec.target_url)
        self._status = LinkStatus("active")

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target(self) -> TargetURL:
        return self._target

    @property
    def status(self) -> LinkStatus:
        return self._status

    def deactivate(self) -> None:
        if self._status == LinkStatus("inactive"):
            raise conflict(
                "already_deactivated", f"short link {self._slug} is already deactivated"
            )
        self._status = LinkStatus("inactive")

    def __eq__(self, other: object) -> Truth:
        return Truth(isinstance(other, ShortLink) and other._slug == self._slug)

    def __hash__(self) -> int:
        return hash(self._slug)
