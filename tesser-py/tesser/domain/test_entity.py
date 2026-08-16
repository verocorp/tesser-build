import pytest

from tesser.domain.entity import Entity


class Named(Entity):

    def __init__(self, key: str, label: str) -> None:
        self._key = key
        self.label = label

    @property
    def identity(self) -> object:
        return self._key


def test_entity_equality_is_identity_not_attributes() -> None:
    assert Named("a", "one") == Named("a", "two")
    assert Named("a", "one") != Named("b", "one")


def test_entity_hash_follows_identity() -> None:
    assert hash(Named("a", "one")) == hash(Named("a", "two"))
    assert len({Named("a", "one"), Named("a", "two")}) == 1


def test_a_different_type_with_the_same_identity_is_not_equal() -> None:
    class Other(Entity):

        def __init__(self, key: str) -> None:
            self._key = key

        @property
        def identity(self) -> object:
            return self._key

    assert Named("a", "one") != Other("a")


def test_an_entity_without_identity_says_so() -> None:
    class Undeclared(Entity):
        pass

    with pytest.raises(NotImplementedError, match="must declare `identity`"):
        Undeclared().identity


def test_a_subclass_may_not_override_the_identity_contract() -> None:
    for name in ("__eq__", "__hash__"):
        with pytest.raises(TypeError, match=f"must not override {name}"):
            type("Custom", (Entity,), {name: lambda self, other=None: True})
