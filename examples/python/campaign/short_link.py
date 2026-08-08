import copy
from dataclasses import dataclass

import tesser.domain as ts

from campaign.link_status import LinkStatus
from campaign.slug import Slug
from campaign.target_url import TargetURL


@dataclass(frozen=True)
class ShortLinkSpec:

    slug: str
    target_url: str
    active: bool


class ShortLink:

    def __init__(self, spec: ShortLinkSpec) -> None:
        try:
            self._slug = Slug(spec.slug)
        except ValueError as e:
            raise ValueError(f"invalid slug: {e}") from e
        try:
            self._target_url = TargetURL(spec.target_url)
        except ValueError as e:
            raise ValueError(f"invalid target url: {e}") from e
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
        if self._status == LinkStatus("inactive"):
            raise ValueError(f"short link {self._slug} is already deactivated")
        self._status = LinkStatus("inactive")

    def _clone(self) -> "ShortLink":
        return copy.copy(self)

    def __eq__(self, other: object) -> ts.Truth:
        return ts.Truth(isinstance(other, ShortLink) and other._slug == self._slug)

    def __hash__(self) -> int:
        return hash(self._slug)
