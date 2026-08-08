from collections.abc import Mapping
from typing import ClassVar

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


def test_construction_is_one_shot_even_through_init_itself() -> None:
    ask = Ask(path="/campaigns")
    with pytest.raises(AttributeError, match=r"already constructed"):
        Ask.__init__(ask, path="/admin")
    with pytest.raises(AttributeError, match=r"already constructed"):
        tesser.srv.Record.__init__(ask, path="/admin")
    assert ask.path == "/campaigns"


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


def test_equality_covers_every_field_a_record_carries() -> None:
    assert Reply(200, b"ok") != Reply(200, b"other")
    assert Ask(path="/x", headers={"a": "b"}) != Ask(path="/x", headers={"a": "c"})
    assert Ask(path="/x", headers={"a": "b"}) != Ask(path="/x")
    assert Ask(path="/x") != Ask(path="/y")


def test_a_misspelled_field_fails_at_construction_not_first_read() -> None:
    class Typoed(tesser.srv.Response):

        def __init__(self, status: int) -> None:
            super().__init__(stauts=status)

        status: int

    with pytest.raises(TypeError, match=r"^Typoed declares no field 'stauts'$"):
        Typoed(200)


def test_records_of_different_types_never_compare_equal() -> None:
    class OtherReply(tesser.srv.Response):

        def __init__(self, status: int, body: bytes = b"") -> None:
            super().__init__(status=status, body=body)

        status: int
        body: bytes

    assert Reply(200, b"") != OtherReply(200, b"")


def test_a_wire_record_is_unhashable_because_it_compares_by_value() -> None:
    with pytest.raises(TypeError):
        hash(Reply(200, b"ok"))
    ask = Ask(headers={"a": "b"})
    with pytest.raises(TypeError):
        hash(ask)
    with pytest.raises(TypeError):
        hash(tuple(sorted(ask.__dict__.items())))


def test_a_record_subclass_may_not_take_over_the_contract() -> None:
    with pytest.raises(
        TypeError,
        match=r"^_Sneaky must not override __setattr__: Record owns the wire-record contract$",
    ):

        class _Sneaky(tesser.srv.Request):

            def __setattr__(self, name: str, value: object) -> None:
                pass

    with pytest.raises(
        TypeError,
        match=r"^_Slotted must not define or inherit __slots__: Record equality reads __dict__$",
    ):

        class _Slotted(tesser.srv.Request):
            __slots__ = ("x",)


def test_a_mixin_listed_before_the_base_may_not_take_over_the_contract_either() -> None:
    class _Mut:

        def __setattr__(self, name: str, value: object) -> None:
            object.__setattr__(self, name, value)

    with pytest.raises(
        TypeError,
        match=r"^_MutAsk must not override __setattr__: Record owns the wire-record contract$",
    ):

        class _MutAsk(_Mut, tesser.srv.Request):
            pass


def test_a_record_subclass_may_not_redefine_equality_or_hashing_or_deletion() -> None:
    with pytest.raises(TypeError):

        class _Loose(tesser.srv.Response):

            def __eq__(self, other: object) -> bool:
                return True

    with pytest.raises(TypeError):

        class _Hashed(tesser.srv.Response):

            def __hash__(self) -> int:
                return 0

    with pytest.raises(TypeError):

        class _Deletable(tesser.srv.Response):

            def __delattr__(self, name: str) -> None:
                return None

    with pytest.raises(TypeError):

        class _Inverted(tesser.srv.Response):

            def __ne__(self, other: object) -> bool:
                return False


def test_a_slotted_mixin_is_refused_even_though_the_subclass_declares_no_slots() -> None:
    class _Compact:
        __slots__ = ("x",)

    with pytest.raises(TypeError):

        class _Mixed(tesser.srv.Request, _Compact):
            pass


def test_a_record_field_may_not_carry_a_class_level_default() -> None:
    with pytest.raises(
        TypeError,
        match=r"^_Defaulted gives field 'status' a class-level default: "
        r"a record field has no default outside __init__$",
    ):

        class _Defaulted(tesser.srv.Response):
            status: int = 200


def test_a_classvar_is_not_a_field_and_cannot_be_shadowed_per_instance() -> None:
    class Tagged(tesser.srv.Response):

        KIND: ClassVar[str] = "reply"

        def __init__(self, status: int) -> None:
            super().__init__(status=status)

        status: int

    with pytest.raises(TypeError, match=r"^Tagged declares no field 'KIND'$"):
        tesser.srv.Record.__init__(Tagged.__new__(Tagged), KIND="pwned")
    assert Tagged(200).KIND == "reply"


def test_an_annotated_mixin_may_not_smuggle_a_defaulted_field() -> None:
    class _Loaded:
        secret: str = "default"

    with pytest.raises(
        TypeError,
        match=r"^_Carrier gives field 'secret' a class-level default: "
        r"a record field has no default outside __init__$",
    ):

        class _Carrier(_Loaded, tesser.srv.Response):
            pass


def test_a_subclass_that_skips_super_init_builds_an_empty_record_no_guard_can_see() -> None:
    class Forgot(tesser.srv.Response):

        def __init__(self, status: int) -> None:
            pass

        status: int

    assert Forgot(200) == Forgot(500)
    assert vars(Forgot(200)) == {}


def test_a_wire_record_reprs_the_fields_it_carries() -> None:
    assert repr(Reply(200, b"ok")) == "Reply(status=200, body=b'ok')"
    assert repr(Ask(path="/x", headers={"a": "b"})) == "Ask(path='/x', headers={'a': 'b'})"


def test_a_wire_record_never_equals_a_plain_object() -> None:
    assert Reply(200, b"ok") != "Reply(200, b'ok')"
    assert Reply(200, b"ok") != object()


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
