import tesser.adapters.repository as repository


def test_repository_is_a_plain_marker_base() -> None:
    class Concrete(repository.Repository):
        pass

    assert issubclass(Concrete, repository.Repository)
    assert repository.Repository.__mro__[1:] == (object,)
    assert not hasattr(repository.Repository, "__slots__")


def test_repository_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(repository.Repository) if not name.startswith("__")}
    assert own == set(), own
