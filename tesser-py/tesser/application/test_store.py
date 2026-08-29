import contextlib
import typing

import tesser.application.store as store


@typing.runtime_checkable
class _Held(typing.Protocol):
    def act(self) -> int: ...


class _HeldImpl:

    def act(self) -> int:
        return 1


@typing.runtime_checkable
class _Opens(store.Store, typing.Protocol):
    def transaction(self) -> typing.AsyncContextManager[_Held]: ...


class _Impl:

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[_Held]:
        yield _HeldImpl()


def test_store_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Opens)
    assert store.Store not in type(_Impl()).__mro__


def test_store_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert store.Store in _Opens.__mro__


def test_store_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(store.Store) if not name.startswith("_")}
    assert own == set(), own
