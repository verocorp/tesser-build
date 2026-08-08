"""The classifier, verified against the (reworked, conformant) worked example.

This is the acceptance gate for pass-1/pass-2 classification: every domain type
in ``examples/python`` must land in the stereotype the design intends, with the
right structural attributes.
"""

import os

from tessercheck.classify import (
    ClassInfo,
    Stereotype,
    classify_paths,
    classify_sources,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXAMPLES = os.path.normpath(os.path.join(_HERE, "..", "..", "examples"))


def _classify(*rel_dirs: str) -> dict[str, ClassInfo]:
    return classify_paths([os.path.join(_EXAMPLES, d) for d in rel_dirs])


def test_link_campaign_domain_classification() -> None:
    reg = _classify("python/campaign", "python/catalog")

    for name in ["Slug", "CampaignID", "CampaignName", "TargetURL", "SKU", "Money", "Labels"]:
        assert reg[name].stereotype is Stereotype.VALUE_OBJECT, name

    for name in ["CampaignSpec", "ShortLinkSpec", "MoneySpec", "ProductSpec"]:
        assert reg[name].stereotype is Stereotype.SPEC, name

    # A fact entity: identity, embeds only VOs (so NOT a root), composed in
    # nothing.
    assert reg["Product"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["Product"].embeds_entity is False
    assert reg["Product"].is_aggregate_root is False
    assert reg["Product"].is_member is False

    # A member entity: identity, embeds only VOs, composed inside the Campaign
    # aggregate — a member is a graph position, still not a root.
    assert reg["ShortLink"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["ShortLink"].is_member is True
    assert reg["ShortLink"].embeds_entity is False
    assert reg["ShortLink"].is_aggregate_root is False

    # An aggregate root: a reference-identity entity that embeds ≥1 entity
    # (Campaign embeds the ShortLink entity) — the settled spec's root signal.
    assert reg["Campaign"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["Campaign"].embeds_entity is True
    assert reg["Campaign"].is_aggregate_root is True
    assert reg["Campaign"].is_member is False


def test_tesser_domain_base_declares_the_stereotype() -> None:
    """A ``tesser.domain`` base is a DECLARATION and outranks the heuristics.

    Regression: the local signals key on ``@dataclass`` and a defined
    ``__eq__``, and a base-class domain object has neither — it is not a
    dataclass and it inherits equality from the base. Every such class fell to
    OTHER, so every classifier-keyed check (TB010-TB018) skipped it silently.
    Both import shapes, aliases included.
    """
    reg = classify_sources(
        {
            "dotted.py": (
                "import tesser.domain as ts\n"
                "class Slug(ts.ValueObject):\n"
                "    _value: str\n"
            ),
            "plain.py": (
                "from tesser.domain import Entity\n"
                "class Order(Entity):\n"
                "    _id: str\n"
            ),
            "aliased.py": (
                "from tesser.domain import AggregateRoot as Root\n"
                "class Basket(Root):\n"
                "    _id: str\n"
            ),
            "spec.py": (
                "import tesser.domain as ts\n"
                "class OrderSpec(ts.Spec):\n"
                "    id: str\n"
            ),
        }
    )
    assert reg["Slug"].stereotype is Stereotype.VALUE_OBJECT
    assert reg["Order"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["Basket"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["OrderSpec"].stereotype is Stereotype.SPEC


def test_unrelated_class_named_valueobject_is_not_a_tesser_value_object() -> None:
    """The base match is on the DOTTED name, not the last segment — a local
    class that happens to be called ``ValueObject`` declares nothing."""
    reg = classify_sources(
        {
            "local.py": (
                "class ValueObject:\n"
                "    pass\n"
                "class Thing(ValueObject):\n"
                "    x: str\n"
            )
        }
    )
    assert reg["Thing"].stereotype is Stereotype.OTHER
