import tesser.domain.aggregate as aggregate
import tesser.domain.entity as entity


def test_aggregate_root_extends_entity() -> None:
    assert issubclass(aggregate.AggregateRoot, entity.Entity)
    assert entity.Entity in aggregate.AggregateRoot.__mro__


def test_aggregate_root_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(aggregate.AggregateRoot) if not name.startswith("__")}
    assert own == set(), own
