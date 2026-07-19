import copy
from dataclasses import dataclass

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
        if not self._active:
            raise ValueError(f"short link {self._slug} is already deactivated")
        self._active = False

    def _clone(self) -> "ShortLink":
        return copy.copy(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
