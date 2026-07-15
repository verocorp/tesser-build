"""The classifier, verified against the (reworked, conformant) worked examples.

This is the acceptance gate for pass-1/pass-2 classification: every domain type
in ``examples/python`` and ``examples/python-expenses`` must land in the
stereotype the design intends, with the right structural attributes.
"""

import os

from ddd_vet.classify import ClassInfo, Stereotype, classify_paths

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

    # A fact entity: identity, owns no collection, composed in nothing.
    assert reg["Product"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["Product"].owns_collection is False
    assert reg["Product"].is_member is False

    # A member entity: identity, composed inside the Campaign aggregate.
    assert reg["ShortLink"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["ShortLink"].is_member is True
    assert reg["ShortLink"].owns_collection is False

    # An aggregate root: identity + owns a collection of domain objects.
    assert reg["Campaign"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["Campaign"].owns_collection is True
    assert reg["Campaign"].is_member is False


def test_expenses_domain_classification() -> None:
    reg = _classify("python-expenses/expenses")

    for name in [
        "DecimalAmount", "Money", "Expense", "Labels",
        "ReportID", "ReportTitle", "ReceiptNumber", "Category",
    ]:
        assert reg[name].stereotype is Stereotype.VALUE_OBJECT, name

    for name in ["MoneySpec", "ExpenseSpec", "ReportSpec"]:
        assert reg[name].stereotype is Stereotype.SPEC, name

    # The aggregate owns a collection of Expense value objects (owning a
    # collection of domain objects — entity OR VO — is the aggregate signal;
    # "embeds an entity" alone would miss this VO-collection case).
    assert reg["ExpenseReport"].stereotype is Stereotype.IDENTITY_OBJECT
    assert reg["ExpenseReport"].owns_collection is True
    assert reg["ExpenseReport"].is_member is False
