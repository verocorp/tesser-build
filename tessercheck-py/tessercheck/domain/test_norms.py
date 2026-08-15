from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks

@ts.helper
def _conforming() -> tuple[tuple[str, str, str, bool], ...]:  # tessercheck:ignore TB073
    return (
        (
            "app/domain/thing.py",
            "app.domain.thing",
            "import tesser.domain as ts\n"
            "class ThingSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class Thing(ts.AggregateRoot):\n"
            "    def __init__(self, spec: ThingSpec) -> None:\n"
            "        self.text = spec.text\n",
            False,
        ),
        (
            "app/client/client.py",
            "app.client.client",
            "import tesser.context as ts\n"
            "class AskRequest(ts.Request):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class AskResponse(ts.Response):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n",
            False,
        ),
        (
            "app/application/service.py",
            "app.application.service",
            "import tesser.application as ts\n"
            "import app.client.client as client\n"
            "class AskService(ts.ApplicationService):\n"
            "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
            "        return client.AskResponse(text=request.text)\n"
            "    def _helper(self, anything: int) -> int:\n"
            "        return anything\n",
            False,
        ),
    )


@ts.helper
def _findings(  # tessercheck:ignore TB073
    sources: tuple[tuple[str, str, str, bool], ...] = (),
    conforming: bool = True,
) -> tuple[str, ...]:
    spec = checks.CodebaseSpec(
        sources=(_conforming() + sources) if conforming else sources,
        declared="app",
        nested=(),
        symlinked=(),
    )
    return tuple(
        f"{violation.path()}:{int(violation.line())}: "
        f"{violation.code()} {violation.text()}"
        for violation in checks.Codebase(spec).violations()
    )


def test_comments_docstrings_and_bare_strings_are_flagged() -> None:
    findings = _findings(
        (
            (
                "tests/test_prose.py",
                "tests.test_prose",
                '"""A docstring."""\n'
                "# a prose comment\n"
                "x: int = 1  # type: ignore\n"
                "def test_ok() -> None:\n"
                "    y = 1\n"
                '    "a bare string"\n'
                "    assert y\n",
                False,
            ),
        )
    )
    assert any(
        "test_prose.py:1: TB020" in f and "carries a docstring; "
        "code speaks for itself — comments, docstrings, and loose strings "
        "belong in the doc layer" in f
        for f in findings
    )
    assert any("test_prose.py:2: TB020" in f and "carries a code comment" in f for f in findings)
    assert any(
        "test_prose.py:6: TB020" in f and "carries a bare string statement" in f
        for f in findings
    )
    assert not any("test_prose.py:3:" in f and "TB020" in f for f in findings)


def test_the_retired_category_marker_is_an_ordinary_comment() -> None:
    findings = _findings(
        (
            (
                "tests/test_marked.py",
                "tests.test_marked",
                "# tesser-category: spec\n"
                "def test_ok() -> None:\n"
                "    assert True\n",
                False,
            ),
        )
    )
    assert any(
        "test_marked.py:1: TB020" in f and "carries a code comment" in f for f in findings
    )


def test_mocking_library_and_patcher_fixtures_are_flagged() -> None:
    findings = _findings(
        (
            (
                "tests/test_mocky.py",
                "tests.test_mocky",
                "from unittest.mock import patch\n"
                "import pytest\n"
                "def test_a(monkeypatch: pytest.MonkeyPatch) -> None:\n"
                "    assert patch\n",
                False,
            ),
        )
    )
    assert any(
        "test_mocky.py:1: TB030" in f and "imports a mocking library; a test double is "
        "a hand-written fake, never a mocking library or a runtime patcher" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "takes the monkeypatch fixture" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "reaches for pytest MonkeyPatch" in f
        for f in findings
    )


def test_a_marked_patcher_seam_is_suppressed() -> None:
    findings = _findings(
        (
            (
                "tests/test_seam.py",
                "tests.test_seam",
                "def test_a(monkeypatch) -> None:  # tessercheck:ignore TB030\n"
                "    assert monkeypatch\n",
                False,
            ),
        )
    )
    assert not any("test_seam" in f for f in findings)


def test_a_called_shadowed_builtin_is_flagged() -> None:
    findings = _findings(
        (
            (
                "tests/test_shadow.py",
                "tests.test_shadow",
                "def test_a() -> None:\n"
                "    id = 'x'\n"
                "    assert id(3)\n"
                "def test_b(len: int = 0) -> None:\n"
                "    assert len == 0\n",
                False,
            ),
        )
    )
    assert any(
        "test_shadow.py:3: TB033" in f and "binds id and calls it in the same scope; "
        "a shadowed builtin is never called — rename the binding" in f
        for f in findings
    )
    assert not any("test_shadow.py:5:" in f and "TB033" in f for f in findings)


def test_string_form_equality_is_flagged() -> None:
    findings = _findings(
        (
            (
                "tests/test_streq.py",
                "tests.test_streq",
                "def test_a() -> None:\n"
                "    a, b = 1, 2\n"
                "    assert str(a) == str(b)\n"
                "    assert str(a) == 'one'\n",
                False,
            ),
        )
    )
    assert any(
        "test_streq.py:3: TB004" in f and "compare value objects by value, "
        "never by their string form" in f
        for f in findings
    )
    assert not any("test_streq.py:4:" in f for f in findings)


def test_a_value_object_mutable_collection_field_is_flagged() -> None:
    findings = _findings(
        (
            (
                "app/domain/bag.py",
                "app.domain.bag",
                "import tesser.domain as ts\n"
                "class Bag(ts.ValueObject):\n"
                "    _items: list[str]\n"
                "    _names: tuple[str, ...]\n"
                "    def __init__(self, item: str) -> None:\n"
                "        object.__setattr__(self, '_items', [item])\n"
                "        object.__setattr__(self, '_names', (item,))\n",
                False,
            ),
        )
    )
    assert any(
        "bag.py:3: TB002" in f and "field _items is a mutable collection; "
        "a value object's field is hashable — a tuple or frozenset, never "
        "a mutable collection" in f
        for f in findings
    )
    assert not any("_names" in f and "TB002" in f for f in findings)


def test_mutable_set_and_quoted_annotations_are_still_mutable_collections() -> None:
    findings = _findings(
        (
            (
                "app/domain/holder.py",
                "app.domain.holder",
                "import tesser.domain as ts\n"
                "from typing import MutableSet\n"
                "class Holder(ts.ValueObject):\n"
                "    _mset: MutableSet[str]\n"
                "    _quoted: 'list[str]'\n"
                "    def __init__(self, item: str) -> None:\n"
                "        object.__setattr__(self, '_mset', {item})\n"
                "        object.__setattr__(self, '_quoted', [item])\n",
                False,
            ),
        )
    )
    assert any("field _mset is a mutable collection" in f for f in findings)
    assert any("field _quoted is a mutable collection" in f for f in findings)


def test_a_value_object_hides_its_representation() -> None:
    findings = _findings(
        (
            (
                "app/domain/leaky.py",
                "app.domain.leaky",
                "import tesser.domain as ts\n"
                "class Leaky(ts.ValueObject):\n"
                "    amount: int\n"
                "    _kept: int\n"
                "    def __init__(self, amount: int) -> None:\n"
                "        object.__setattr__(self, 'amount', amount)\n"
                "        object.__setattr__(self, '_kept', amount)\n"
                "    def kept(self) -> int:\n"
                "        return self._kept\n",
                False,
            ),
        )
    )
    assert any(
        "leaky.py:3: TB010" in f and "exposes field amount; a value object hides its "
        "representation — a public field belongs on a spec" in f
        for f in findings
    )
    assert any(
        "TB010" in f and "Leaky.kept passes the raw primitive through; "
        "a value object's accessor returns a value object — "
        "the canonical exit is the only primitive door" in f
        for f in findings
    )


def test_an_accessor_never_hands_back_the_backing_collection() -> None:
    findings = _findings(
        (
            (
                "app/domain/box.py",
                "app.domain.box",
                "import tesser.domain as ts\n"
                "class BoxSpec(ts.Spec):\n"
                "    def __init__(self, item: str) -> None:\n"
                "        self.item = item\n"
                "class Box(ts.AggregateRoot):\n"
                "    _items: list[str]\n"
                "    def __init__(self, spec: BoxSpec) -> None:\n"
                "        self._items = [spec.item]\n"
                "    def items(self) -> list[str]:\n"
                "        return self._items\n",
                False,
            ),
        )
    )
    assert any(
        "TB011" in f and "Box.items hands back its backing collection; an accessor "
        "returns a defensive copy, never the backing store" in f
        for f in findings
    )


def test_an_aggregate_is_referenced_by_id_never_held() -> None:
    findings = _findings(
        (
            (
                "app/domain/pair.py",
                "app.domain.pair",
                "import tesser.domain as ts\n"
                "import app.domain.thing as thing\n"
                "class PairSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Pair(ts.AggregateRoot):\n"
                "    _other: thing.Thing\n"
                "    def __init__(self, spec: PairSpec) -> None:\n"
                "        self._other = thing.Thing(thing.ThingSpec(text=spec.text))\n",
                False,
            ),
        )
    )
    assert any(
        "TB012" in f and "Pair field _other holds another aggregate root; an aggregate "
        "is referenced by its ID value object, never held" in f
        for f in findings
    )


def test_exit_norms_leaf_and_structured() -> None:
    findings = _findings(
        (
            (
                "app/domain/exits.py",
                "app.domain.exits",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class GoodLeaf(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "class WrongExit(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __int__(self) -> int:\n"
                "        return 0\n"
                "class HandRolled(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return self._value.upper()\n"
                "class Compound(ts.ValueObject):\n"
                "    _a: GoodLeaf\n"
                "    _b: GoodLeaf\n"
                "    def __init__(self, a: str, b: str) -> None:\n"
                "        object.__setattr__(self, '_a', GoodLeaf(a))\n"
                "        object.__setattr__(self, '_b', GoodLeaf(b))\n"
                "    def __str__(self) -> str:\n"
                "        return 'x'\n",
                False,
            ),
        )
    )
    assert not any("GoodLeaf" in f and "TB015" in f for f in findings)
    assert not any("GoodLeaf" in f and "TB018" in f for f in findings)
    assert any(
        "TB015" in f and "WrongExit.__int__ is a mismatched exit; a leaf defines exactly "
        "its backing type's conversion dunder" in f
        for f in findings
    )
    assert any(
        "TB018" in f and "HandRolled.__str__ hand-rolls its exit; a canonical exit is a "
        "one-line delegation to its canonical_* policy" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Compound.__str__ is a primitive exit; a structured domain "
        "object has no primitive exit — decompose through leaf components" in f
        for f in findings
    )


def test_composition_norms() -> None:
    findings = _findings(
        (
            (
                "app/domain/shapes.py",
                "app.domain.shapes",
                "import tesser.domain as ts\n"
                "class Flag(ts.ValueObject):\n"
                "    _value: bool\n"
                "    def __init__(self, value: bool) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "class Mixed(ts.ValueObject):\n"
                "    _raw: str\n"
                "    _on: bool\n"
                "    def __init__(self, raw: str, on: bool) -> None:\n"
                "        object.__setattr__(self, '_raw', raw)\n"
                "        object.__setattr__(self, '_on', on)\n",
                False,
            ),
        )
    )
    assert any(
        "TB016" in f and "Flag field _value is a bool; bool and complex are not "
        "value-object material — model the raw value or reach for an enum" in f
        for f in findings
    )
    assert any(
        "TB016" in f and "Mixed field _raw is a bare primitive; a compound backs "
        "itself with child value objects" in f
        for f in findings
    )
    assert any("TB016" in f and "Mixed field _on is a bool" in f for f in findings)


def test_a_value_object_has_one_construction_door() -> None:
    findings = _findings(
        (
            (
                "app/domain/doors.py",
                "app.domain.doors",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class Slug(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    @classmethod\n"
                "    def parse(cls, raw: str) -> 'Slug':\n"
                "        return cls(raw.strip())\n",
                False,
            ),
        )
    )
    assert any(
        "TB017" in f and "Slug.parse is a second construction door; a value object has "
        "one door — its own __init__" in f
        for f in findings
    )


def test_domain_returns_and_spec_returns() -> None:
    findings = _findings(
        (
            (
                "app/domain/returns.py",
                "app.domain.returns",
                "import tesser.domain as ts\n"
                "class WidgetSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Widget(ts.Entity):\n"
                "    def __init__(self, spec: WidgetSpec) -> None:\n"
                "        self._text = spec.text\n"
                "    def label(self) -> str:\n"
                "        return self._text.upper()\n"
                "    def snapshot(self) -> WidgetSpec:\n"
                "        return WidgetSpec(text=self._text)\n"
                "    def touch(self) -> None:\n"
                "        return None\n",
                False,
            ),
        )
    )
    assert any(
        "TB019" in f and "Widget.label returns str; a domain object's public behavior "
        "hands back domain objects — the licensed exits are the protocol dunders, "
        "the canonical exit, and a -> None transition" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Widget.snapshot returns a spec; a domain object never "
        "serializes itself — a spec is construction data, not an exit" in f
        for f in findings
    )
    assert not any("Widget.touch" in f for f in findings)


def test_review_pins_for_the_shape_norms() -> None:
    findings = _findings(
        (
            (
                "app/domain/pins.py",
                "app.domain.pins",
                "import tesser.domain as ts\n"
                "from typing import ClassVar, Self\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class SelfDoor(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    @classmethod\n"
                "    def parse(cls, raw: str) -> Self:\n"
                "        return cls(raw)\n"
                "    @classmethod\n"
                "    def bare_door(cls, raw):  # type: ignore[no-untyped-def]\n"
                "        return cls(raw)\n"
                "    @classmethod\n"
                "    def kind(cls) -> type['SelfDoor']:\n"
                "        return cls\n"
                "class Quoted(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    def label(self) -> 'str':\n"
                "        return self._value.upper()\n"
                "class Marked(ts.ValueObject):\n"
                "    _kinds: ClassVar[tuple[str, ...]] = ()\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n",
                False,
            ),
        )
    )
    assert any("SelfDoor.parse is a second construction door" in f for f in findings)
    assert any("SelfDoor.bare_door is a second construction door" in f for f in findings)
    assert not any("SelfDoor.kind" in f for f in findings)
    assert any(
        "Quoted.label returns str" in f and "TB019" in f for f in findings
    )
    assert not any("Marked" in f for f in findings)


def test_module_qualified_canonical_delegation_passes() -> None:
    findings = _findings(
        (
            (
                "app/domain/policy.py",
                "app.domain.policy",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n",
                False,
            ),
            (
                "app/domain/word.py",
                "app.domain.word",
                "import tesser.domain as ts\n"
                "import app.domain.policy as policy\n"
                "class Word(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return policy.canonical_str(self._value)\n",
                False,
            ),
        )
    )
    assert not any("Word" in f for f in findings)


def test_undeclared_backing_collection_is_still_caught() -> None:
    findings = _findings(
        (
            (
                "app/domain/sack.py",
                "app.domain.sack",
                "import tesser.domain as ts\n"
                "class SackSpec(ts.Spec):\n"
                "    def __init__(self, item: str) -> None:\n"
                "        self.item = item\n"
                "class Sack(ts.AggregateRoot):\n"
                "    def __init__(self, spec: SackSpec) -> None:\n"
                "        self._items = [spec.item]\n"
                "    def items(self) -> list[str]:\n"
                "        return self._items\n",
                False,
            ),
        )
    )
    assert any(
        "TB011" in f and "Sack.items hands back its backing collection" in f
        for f in findings
    )
