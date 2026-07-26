import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str
    active: bool = True


class ShortLink:
    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = spec.slug

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)


def _link(slug: str = "spring-sale") -> ShortLink:
    return ShortLink(ShortLinkSpec(slug=slug, target_url="https://a.example"))


def _encode(spec: ShortLinkSpec) -> bytes:
    return json.dumps({"slug": spec.slug}).encode("utf-8")


# tesser-category: builder
def _mislabeled(slug: str = "spring-sale") -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example")


def test_helpers_that_do_not_classify_are_reported() -> None:
    assert _link().__eq__(_link())
    assert _encode(_mislabeled()) == b'{"slug": "spring-sale"}'
