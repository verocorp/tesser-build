from collections.abc import Mapping

import pytest

import tesser.srv


class Ask(tesser.srv.Request):

    def __init__(self, path: str = "/", headers: Mapping[str, str] | None = None) -> None:
        super().__init__(path=path, headers=dict(headers or {}))

    path: str
    headers: Mapping[str, str]


class Reply(tesser.srv.Response):

    def __init__(self, status: int, body: bytes = b"") -> None:
        super().__init__(status=status, body=body)

    status: int
    body: bytes


class _WriteOnce:

    def __setattr__(self, name: str, value: object) -> None:
        if name in self.__dict__:
            raise AttributeError(f"cannot rebind {name!r}")
        super().__setattr__(name, value)


class _WriteOnceAsk(_WriteOnce):

    def __init__(self, path: str) -> None:
        self.path = path

    path: str


def test_a_wire_record_blocks_rebinding_after_construction() -> None:
    ask = Ask(path="/campaigns")
    with pytest.raises(AttributeError):
        ask.path = "/admin"
    with pytest.raises(AttributeError):
        del ask.path
    assert ask.path == "/campaigns"


def test_a_wire_record_blocks_new_fields_after_construction() -> None:
    ask = Ask(path="/campaigns")
    with pytest.raises(AttributeError):
        setattr(ask, "verdict", "allowed")
    assert "verdict" not in vars(ask)


def test_write_once_lost_because_it_leaves_the_smuggling_channel_open() -> None:
    ask = _WriteOnceAsk("/campaigns")
    with pytest.raises(AttributeError):
        ask.path = "/admin"
    setattr(ask, "verdict", "allowed")
    assert vars(ask)["verdict"] == "allowed"


def test_wire_records_compare_by_value() -> None:
    assert Reply(200, b"ok") == Reply(200, b"ok")
    assert Reply(200, b"ok") != Reply(404, b"ok")
    assert Ask(path="/x", headers={"a": "b"}) == Ask(path="/x", headers={"a": "b"})


def test_records_of_different_types_never_compare_equal() -> None:
    class OtherReply(tesser.srv.Response):

        def __init__(self, status: int, body: bytes = b"") -> None:
            super().__init__(status=status, body=body)

        status: int
        body: bytes

    assert Reply(200, b"") != OtherReply(200, b"")


def test_a_wire_record_is_unhashable_because_it_carries_containers() -> None:
    ask = Ask(headers={"a": "b"})
    with pytest.raises(TypeError):
        hash(ask)
    with pytest.raises(TypeError):
        hash(tuple(sorted(ask.__dict__.items())))


def test_a_record_subclass_may_not_take_over_the_contract() -> None:
    with pytest.raises(TypeError):

        class _Sneaky(tesser.srv.Request):

            def __setattr__(self, name: str, value: object) -> None:
                pass

    with pytest.raises(TypeError):

        class _Slotted(tesser.srv.Request):
            __slots__ = ("x",)


def test_a_derived_field_uses_the_valueobject_idiom() -> None:
    class Sized(tesser.srv.Response):

        def __init__(self, body: bytes) -> None:
            super().__init__(body=body)
            object.__setattr__(self, "size", len(body))

        body: bytes
        size: int

    reply = Sized(b"abc")
    assert reply.size == 3
    with pytest.raises(AttributeError):
        reply.size = 0
