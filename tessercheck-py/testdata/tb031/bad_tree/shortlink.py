from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:

    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("invalid slug: must not be empty")

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class TargetURL:

    _value: str

    def __post_init__(self) -> None:
        if not self._value.startswith("https://"):
            raise ValueError("invalid target url: must start with https://")

    def __str__(self) -> str:
        return self._value


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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
