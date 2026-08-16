from tesser.srv.host import Host


def test_host_is_a_plain_marker_base() -> None:
    class Concrete(Host):
        pass

    assert issubclass(Concrete, Host)
    assert Host.__mro__[1:] == (object,)
    assert not hasattr(Host, "__slots__")


def test_host_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Host) if not name.startswith("__")}
    assert own == set(), own
