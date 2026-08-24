import tesser.adapters.gateway as gateway


def test_gateway_is_a_plain_marker_base() -> None:
    class Concrete(gateway.Gateway):
        pass

    assert issubclass(Concrete, gateway.Gateway)
    assert gateway.Gateway.__mro__[1:] == (object,)
    assert not hasattr(gateway.Gateway, "__slots__")


def test_gateway_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(gateway.Gateway) if not name.startswith("__")}
    assert own == set(), own
