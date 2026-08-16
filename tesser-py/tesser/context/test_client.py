from typing import Protocol, runtime_checkable

from tesser.context.client import Client


@runtime_checkable
class _Shaped(Client, Protocol):
    def act(self) -> int: ...


class _Impl:

    def act(self) -> int:
        return 1


def test_client_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert Client not in type(_Impl()).__mro__


def test_client_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert Client in _Shaped.__mro__


def test_client_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Client) if not name.startswith("_")}
    assert own == set(), own
