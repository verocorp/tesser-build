import typing

import tesser.application.port as port
import tesser.application.relay as relay


@typing.runtime_checkable
class _Shaped(relay.Relay, typing.Protocol):
    def act(self) -> int: ...


class _Impl:

    def act(self) -> int:
        return 1


def test_relay_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert relay.Relay not in type(_Impl()).__mro__


def test_relay_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert relay.Relay in _Shaped.__mro__


def test_a_relay_is_not_a_port() -> None:
    assert port.Port not in relay.Relay.__mro__
    assert relay.Relay not in port.Port.__mro__


def test_relay_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(relay.Relay) if not name.startswith("_")}
    assert own == set(), own
