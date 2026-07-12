import pytest

from expenses.identifiers import Category, ReceiptNumber, ReportID, ReportTitle
from expenses.labels import Labels


def test_report_id_generate_is_unique() -> None:
    a = ReportID.generate()
    b = ReportID.generate()
    assert a != b


def test_report_id_equality() -> None:
    assert ReportID("abc") == ReportID("abc")
    assert ReportID("abc") != ReportID("def")


def test_report_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ReportID("")


def test_report_title_equality() -> None:
    assert ReportTitle("Trip to NYC") == ReportTitle("Trip to NYC")
    assert ReportTitle("Trip to NYC") != ReportTitle("Trip to SF")


def test_report_title_rejects_blank() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ReportTitle("   ")


def test_receipt_number_equality() -> None:
    assert ReceiptNumber("R-1") == ReceiptNumber("R-1")
    assert ReceiptNumber("R-1") != ReceiptNumber("R-2")


def test_receipt_number_rejects_blank() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ReceiptNumber("")


def test_category_equality() -> None:
    assert Category("travel") == Category("travel")
    assert Category("travel") != Category("meals")


def test_category_rejects_blank() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Category("")


def test_category_str() -> None:
    assert str(Category("travel")) == "travel"


def test_labels_equality_regardless_of_insertion_order() -> None:
    a = Labels.new({"project": "apollo", "team": "nav"})
    b = Labels.new({"team": "nav", "project": "apollo"})
    assert a == b
    assert hash(a) == hash(b)


def test_labels_inequality() -> None:
    a = Labels.new({"project": "apollo"})
    b = Labels.new({"project": "gemini"})
    assert a != b


def test_labels_default_is_empty() -> None:
    assert Labels.new().as_dict() == {}
    assert Labels.new(None).as_dict() == {}


def test_labels_as_dict_is_a_copy() -> None:
    labels = Labels.new({"project": "apollo"})
    out = labels.as_dict()
    out["project"] = "mutated"
    assert labels.as_dict() == {"project": "apollo"}  # original unaffected
