import typing

import tesser.context.client as client


@typing.runtime_checkable
class _Shaped(client.Client, typing.Protocol):
    def act(self) -> int: ...


class _Impl:

    def act(self) -> int:
        return 1


def test_client_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert client.Client not in type(_Impl()).__mro__


def test_client_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert client.Client in _Shaped.__mro__


def test_client_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(client.Client) if not name.startswith("_")}
    assert own == set(), own
