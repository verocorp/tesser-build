from typing import Protocol, runtime_checkable

from tesser.srv.port import Port


@runtime_checkable
class _Shaped(Port, Protocol):
    def act(self) -> int: ...


class _Impl:

    def act(self) -> int:
        return 1


def test_port_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert Port not in type(_Impl()).__mro__


def test_port_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert Port in _Shaped.__mro__


def test_port_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Port) if not name.startswith("_")}
    assert own == set(), own
