import tesser.srv.host as host


def test_host_is_a_plain_marker_base() -> None:
    class Concrete(host.Host):
        pass

    assert issubclass(Concrete, host.Host)
    assert host.Host.__mro__[1:] == (object,)
    assert not hasattr(host.Host, "__slots__")


def test_host_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(host.Host) if not name.startswith("__")}
    assert own == set(), own
