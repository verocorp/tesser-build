import pytest

import tesser.domain as ts


class Color(ts.ValueObject):

    _name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)


class SpecialColor(Color):
    pass


class Point(ts.ValueObject):

    _x: int
    _y: int

    def __init__(self, x: int, y: int) -> None:
        object.__setattr__(self, "_x", x)
        object.__setattr__(self, "_y", y)


def test_equality_covers_every_stored_field() -> None:
    assert Point(1, 2) == Point(1, 2)
    assert Point(1, 2) != Point(1, 3)
    assert Point(1, 2) != Point(2, 2)


def test_equality_requires_exact_type() -> None:
    assert Color("red") != SpecialColor("red")
    assert SpecialColor("red") != Color("red")
    other: object = "red"
    assert Color("red") != other
    assert Color("red").__eq__("red") is NotImplemented


def test_hash_follows_equality() -> None:
    assert hash(Point(1, 2)) == hash(Point(1, 2))
    assert len({Point(1, 2), Point(1, 2), Point(1, 3)}) == 2


def test_hash_distinguishes_fields_and_type() -> None:
    assert hash(Point(1, 2)) != hash(Point(1, 3))
    assert hash(Color("red")) != hash(SpecialColor("red"))


def test_immutable_after_construction() -> None:
    point = Point(1, 2)
    with pytest.raises(AttributeError, match=r"Point is immutable: cannot set '_x'"):
        point._x = 9
    with pytest.raises(AttributeError, match=r"Point is immutable: cannot delete '_y'"):
        del point._y
    assert point == Point(1, 2)


def test_repr_names_type_and_fields() -> None:
    assert repr(Color("red")) == "Color(_name='red')"
    assert repr(Point(1, 2)) == "Point(_x=1, _y=2)"
