from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str
    active: bool = True


def _spec(slug: str = "spring-sale", active: bool = True) -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example", active=active)


def _specs(count: int = 1) -> tuple[ShortLinkSpec, ...]:
    return tuple(_spec(slug=f"link-{n}") for n in range(count))


@pytest.fixture()
def base_slug() -> str:
    return "spring-sale"


# tesser-category: dto
def _view(slug: str = "spring-sale") -> dict[str, str]:
    return {"slug": slug}


def _payload(slug: str = "spring-sale") -> bytes:  # tesser-category: dto
    return slug.encode("utf-8")


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[ShortLinkSpec] = []

    def save(self, spec: ShortLinkSpec) -> None:
        self.saved.append(spec)

    def load(self, slug: str) -> ShortLinkSpec:
        raise LookupError(slug)


def test_spec_helper_supplies_defaults(base_slug: str) -> None:
    assert _spec().slug == base_slug
    assert _spec(slug="autumn-sale").slug == "autumn-sale"
    assert len(_specs(count=2)) == 2


def test_fake_records_what_it_is_given() -> None:
    repo = FakeRepo()
    repo.save(_spec())
    assert repo.saved == [_spec()]


def test_declared_helpers_need_no_structural_signal() -> None:
    assert _view()["slug"] == "spring-sale"
    assert _payload() == b"spring-sale"

    def inner(n: int = 1) -> int:
        return n

    assert inner() == 1
