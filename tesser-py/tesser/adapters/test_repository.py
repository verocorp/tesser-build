from tesser.adapters.repository import Repository


def test_repository_is_a_plain_marker_base() -> None:
    class Concrete(Repository):
        pass

    assert issubclass(Concrete, Repository)
    assert Repository.__mro__[1:] == (object,)
    assert not hasattr(Repository, "__slots__")


def test_repository_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Repository) if not name.startswith("__")}
    assert own == set(), own
