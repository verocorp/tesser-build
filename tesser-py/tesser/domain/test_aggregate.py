from tesser.domain.aggregate import AggregateRoot
from tesser.domain.entity import Entity


def test_aggregate_root_extends_entity() -> None:
    assert issubclass(AggregateRoot, Entity)
    assert Entity in AggregateRoot.__mro__


def test_aggregate_root_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(AggregateRoot) if not name.startswith("__")}
    assert own == set(), own
