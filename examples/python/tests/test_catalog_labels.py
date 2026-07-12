import pytest

from catalog.labels import Labels


def test_nil_normalizes_to_empty() -> None:
    assert len(Labels.new(None)) == 0
    assert len(Labels.new()) == 0


def test_equality_is_content_based_regardless_of_order() -> None:
    a = Labels.new({"color": "black", "size": "M"})
    b = Labels.new({"size": "M", "color": "black"})
    assert a == b
    assert hash(a) == hash(b)  # hashable: usable as a dict key / set member
    assert a != Labels.new({"color": "black"})


def test_copies_input_defensively() -> None:
    src = {"color": "black"}
    labels = Labels.new(src)
    src["color"] = "white"  # mutating the source must not affect the value object
    assert labels.get("color") == "black"


def test_as_dict_copies_out_defensively() -> None:
    labels = Labels.new({"color": "black"})
    out = labels.as_dict()
    out["color"] = "white"  # mutating the returned dict must not affect the VO
    assert labels.get("color") == "black"


def test_require_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Labels.require(None)
    assert Labels.require({"color": "black"}).get("color") == "black"
