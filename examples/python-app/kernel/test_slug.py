import pytest

from kernel.slug import Slug
from tesser.errors import DomainError


def test_a_slug_validates_on_construction() -> None:
    with pytest.raises(DomainError):
        Slug("")
    with pytest.raises(DomainError):
        Slug("Has-Caps")
    with pytest.raises(DomainError):
        Slug("-leading")
    assert str(Slug("promo-2026")) == "promo-2026"


def test_slug_equality_is_value_equality() -> None:
    assert Slug("promo") == Slug("promo")
    assert Slug("promo") != Slug("other")
    assert hash(Slug("promo")) == hash(Slug("promo"))
