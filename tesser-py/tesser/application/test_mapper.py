from tesser.application.mapper import Mapper


def test_mapper_is_a_plain_marker_base() -> None:
    class Concrete(Mapper):
        pass

    assert issubclass(Concrete, Mapper)
    assert Mapper.__mro__[1:] == (object,)
    assert not hasattr(Mapper, "__slots__")


def test_mapper_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Mapper) if not name.startswith("__")}
    assert own == set(), own
