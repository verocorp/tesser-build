from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str
    active: bool = True


def _spec(slug: str = "spring-sale", active: bool = True) -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example", active=active)


@pytest.fixture()
def base_slug() -> str:
    return "spring-sale"


# tesser-category: dto
def _view(slug: str = "spring-sale") -> dict[str, str]:
    return {"slug": slug}


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


def test_fake_records_what_it_is_given() -> None:
    repo = FakeRepo()
    repo.save(_spec())
    assert repo.saved == [_spec()]
    assert _view()["slug"] == "spring-sale"
