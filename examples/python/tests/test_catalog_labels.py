import pytest

from catalog.labels import Labels


def test_nil_normalizes_to_empty() -> None:
    assert len(Labels.new(None)) == 0
    assert len(Labels.new()) == 0


def test_equality_is_content_based_regardless_of_order() -> None:
    a = Labels.new({"color": "black", "size": "M"})
    b = Labels.new({"size": "M", "color": "black"})
    assert a == b
    assert hash(a) == hash(b)
    assert a != Labels.new({"color": "black"})


def test_copies_input_defensively() -> None:
    src = {"color": "black"}
    labels = Labels.new(src)
    src["color"] = "white"
    assert labels.get("color") == "black"


def test_as_dict_copies_out_defensively() -> None:
    labels = Labels.new({"color": "black"})
    out = labels.as_dict()
    out["color"] = "white"
    assert labels.get("color") == "black"


def test_require_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Labels.require(None)
    assert Labels.require({"color": "black"}).get("color") == "black"


def test_raw_constructor_with_duplicate_keys_canonicalizes() -> None:
    dup = Labels((("a", "1"), ("a", "2")))
    assert dup == Labels.new({"a": "2"})
    assert hash(dup) == hash(Labels.new({"a": "2"}))
    assert dup.as_dict() == {"a": "2"}


def test_str_is_sorted_display() -> None:
    assert str(Labels.new({"size": "M", "color": "black"})) == "color=black,size=M"
