from tesser.adapters.gateway import Gateway


def test_gateway_is_a_plain_marker_base() -> None:
    class Concrete(Gateway):
        pass

    assert issubclass(Concrete, Gateway)
    assert Gateway.__mro__[1:] == (object,)
    assert not hasattr(Gateway, "__slots__")


def test_gateway_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Gateway) if not name.startswith("__")}
    assert own == set(), own
