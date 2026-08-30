import pytest

import tesser.context.request as request


def test_request_is_a_plain_marker_base() -> None:
    class Concrete(request.Request):
        pass

    assert issubclass(Concrete, request.Request)
    assert request.Request.__mro__[1:] == (object,)
    assert not hasattr(request.Request, "__slots__")


def test_request_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(request.Request) if not name.startswith("__")}
    assert own == set(), own


def test_requests_compare_by_field_values() -> None:
    class Concrete(request.Request):
        def __init__(self, name: str, count: int) -> None:
            self.name = name
            self.count = count

    assert Concrete("a", 1) == Concrete("a", 1)
    assert Concrete("a", 1) != Concrete("a", 2)
    assert hash(Concrete("a", 1)) == hash(Concrete("a", 1))


def test_requests_of_different_types_never_compare_equal() -> None:
    class One(request.Request):
        def __init__(self, name: str) -> None:
            self.name = name

    class Other(request.Request):
        def __init__(self, name: str) -> None:
            self.name = name

    assert One("a") != Other("a")


def test_a_nested_request_compares_through_its_children() -> None:
    class Child(request.Request):
        def __init__(self, value: str) -> None:
            self.value = value

    class Parent(request.Request):
        def __init__(self, child: Child, children: tuple[Child, ...]) -> None:
            self.child = child
            self.children = children

    assert Parent(Child("x"), (Child("y"),)) == Parent(Child("x"), (Child("y"),))
    assert Parent(Child("x"), (Child("y"),)) != Parent(Child("x"), (Child("z"),))
    assert hash(Parent(Child("x"), (Child("y"),))) == hash(Parent(Child("x"), (Child("y"),)))


def test_a_request_with_an_unhashable_field_cannot_be_hashed() -> None:
    class Concrete(request.Request):
        def __init__(self, items: list[str]) -> None:
            self.items = items

    with pytest.raises(TypeError):
        hash(Concrete(["a"]))


def test_a_request_subclass_may_not_redefine_equality_or_hashing() -> None:
    with pytest.raises(TypeError):

        class BadEq(request.Request):
            def __eq__(self, other: object) -> bool:
                return True

    with pytest.raises(TypeError):

        class BadHash(request.Request):
            def __hash__(self) -> int:
                return 0
