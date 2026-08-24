import tesser.application.mapper as mapper


def test_mapper_is_a_plain_marker_base() -> None:
    class Concrete(mapper.Mapper):
        pass

    assert issubclass(Concrete, mapper.Mapper)
    assert mapper.Mapper.__mro__[1:] == (object,)
    assert not hasattr(mapper.Mapper, "__slots__")


def test_mapper_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(mapper.Mapper) if not name.startswith("__")}
    assert own == set(), own
