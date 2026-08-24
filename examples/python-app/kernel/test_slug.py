import pytest

import kernel.slug as slug
import tesser.errors as errors


def test_a_slug_validates_on_construction() -> None:
    with pytest.raises(errors.DomainError):
        slug.Slug("")
    with pytest.raises(errors.DomainError):
        slug.Slug("Has-Caps")
    with pytest.raises(errors.DomainError):
        slug.Slug("-leading")
    assert str(slug.Slug("promo-2026")) == "promo-2026"


def test_slug_equality_is_value_equality() -> None:
    assert slug.Slug("promo") == slug.Slug("promo")
    assert slug.Slug("promo") != slug.Slug("other")
    assert hash(slug.Slug("promo")) == hash(slug.Slug("promo"))
