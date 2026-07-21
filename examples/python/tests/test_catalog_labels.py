from catalog.labels import Labels


def test_empty_is_legal() -> None:
    assert len(Labels({})) == 0


def test_equality_is_content_based_regardless_of_order() -> None:
    a = Labels({"color": "black", "size": "M"})
    b = Labels({"size": "M", "color": "black"})
    assert a == b
    assert hash(a) == hash(b)
    assert a != Labels({"color": "black"})


def test_copies_input_defensively() -> None:
    src = {"color": "black"}
    labels = Labels(src)
    src["color"] = "white"
    assert labels.get("color") == "black"


def test_as_dict_copies_out_defensively() -> None:
    labels = Labels({"color": "black"})
    out = labels.as_dict()
    out["color"] = "white"
    assert labels.get("color") == "black"


def test_single_construction_door() -> None:
    for name in ("new", "require", "from_spec", "parse", "of"):
        assert name not in Labels.__dict__


def test_collection_vo_has_no_conversion_dunders() -> None:
    labels = Labels({"size": "M", "color": "black"})
    for name in ("__str__", "__int__", "__float__", "__bytes__"):
        assert name not in Labels.__dict__
    assert labels.as_dict() == {"size": "M", "color": "black"}
