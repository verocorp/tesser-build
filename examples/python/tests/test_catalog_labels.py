from catalog.labels import LabelValue, Labels


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
    assert labels.get("color") == LabelValue("black")


def test_reader_hands_back_a_value_object_not_the_representation() -> None:
    labels = Labels({"color": "black"})
    assert labels.get("color") == LabelValue("black")
    assert labels.get("absent") is None


def test_single_construction_door() -> None:
    factories = [
        name
        for name, member in vars(Labels).items()
        if isinstance(member, (classmethod, staticmethod))
    ]
    assert factories == []


def test_collection_vo_has_no_conversion_dunders() -> None:
    labels = Labels({"size": "M", "color": "black"})
    for name in ("__str__", "__int__", "__float__", "__bytes__"):
        assert name not in Labels.__dict__
    assert labels.get("size") == LabelValue("M")
