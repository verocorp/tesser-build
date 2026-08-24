import tesser.app.loader as loader


def test_loader_is_a_plain_marker_base() -> None:
    class Concrete(loader.Loader):
        pass

    assert issubclass(Concrete, loader.Loader)
    assert loader.Loader.__mro__[1:] == (object,)


def test_loader_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(loader.Loader) if not name.startswith("__")}
    assert own == set(), own
