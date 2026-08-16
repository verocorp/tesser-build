from tesser.app.loader import Loader


def test_loader_is_a_plain_marker_base() -> None:
    class Concrete(Loader):
        pass

    assert issubclass(Concrete, Loader)
    assert Loader.__mro__[1:] == (object,)


def test_loader_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Loader) if not name.startswith("__")}
    assert own == set(), own
