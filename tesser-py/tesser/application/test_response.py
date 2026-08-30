import tesser.application.response as response


def test_response_is_a_plain_marker_base() -> None:
    class Concrete(response.Response):
        pass

    assert issubclass(Concrete, response.Response)
    assert response.Response.__mro__[1:] == (object,)
    assert not hasattr(response.Response, "__slots__")


def test_response_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(response.Response) if not name.startswith("__")}
    assert own == set(), own


def test_responses_compare_by_field_values() -> None:
    class Concrete(response.Response):
        def __init__(self, name: str, count: int) -> None:
            self.name = name
            self.count = count

    assert Concrete("a", 1) == Concrete("a", 1)
    assert Concrete("a", 1) != Concrete("a", 2)
    assert hash(Concrete("a", 1)) == hash(Concrete("a", 1))


def test_responses_of_different_types_never_compare_equal() -> None:
    class One(response.Response):
        def __init__(self, name: str) -> None:
            self.name = name

    class Other(response.Response):
        def __init__(self, name: str) -> None:
            self.name = name

    assert One("a") != Other("a")


def test_a_nested_response_compares_through_its_children() -> None:
    class Child(response.Response):
        def __init__(self, value: str) -> None:
            self.value = value

    class Parent(response.Response):
        def __init__(self, child: Child, children: tuple[Child, ...]) -> None:
            self.child = child
            self.children = children

    assert Parent(Child("x"), (Child("y"),)) == Parent(Child("x"), (Child("y"),))
    assert Parent(Child("x"), (Child("y"),)) != Parent(Child("x"), (Child("z"),))
