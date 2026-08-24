import typing

import tesser.srv.port as port


@typing.runtime_checkable
class _Shaped(port.Port, typing.Protocol):
    def act(self) -> int: ...


class _Impl:

    def act(self) -> int:
        return 1


def test_port_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert port.Port not in type(_Impl()).__mro__


def test_port_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert port.Port in _Shaped.__mro__


def test_port_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(port.Port) if not name.startswith("_")}
    assert own == set(), own
