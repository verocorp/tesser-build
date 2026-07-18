"""The classifier, verified against the (reworked, conformant) worked example.

This is the acceptance gate for pass-1/pass-2 classification: every domain type
in ``examples/python`` must land in the stereotype the design intends, with the
right structural attributes.
"""

import os

from tessercheck.classify import ClassInfo, Stereotype, classify_paths

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
