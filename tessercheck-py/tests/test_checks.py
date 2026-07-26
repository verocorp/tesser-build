"""Per-check good/bad behavior, the test-scoping exemption, and suppression."""

import ast
from pathlib import Path

import pytest

from tessercheck.checks import check_source
from tessercheck.comments_check import check_comments
from tessercheck.finding import CHECKS, Finding
from tessercheck.helpers_check import _comment_lines
from tessercheck.run import run_source
from tessercheck.shadowing_check import _scope_roots, _suppressed_lines

_TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def _fixture(code: str, kind: str) -> tuple[str, str]:
    path = _TESTDATA / code.lower() / f"{kind}.py"
    return str(path), path.read_text(encoding="utf-8")


@pytest.mark.parametrize("meta", CHECKS, ids=lambda m: m.code)
def test_bad_fixture_trips_only_its_own_code(meta: object) -> None:
    code = meta.code  # type: ignore[attr-defined]
    path, source = _fixture(code, "bad")
    findings = check_source(path, source, is_test=False)
    produced = {f.code for f in findings}
    assert produced == {code}, f"{code} bad.py produced {produced}, expected {{{code}}}"


@pytest.mark.parametrize("meta", CHECKS, ids=lambda m: m.code)
def test_good_fixture_is_clean(meta: object) -> None:
    code = meta.code  # type: ignore[attr-defined]
    path, source = _fixture(code, "good")
    findings = check_source(path, source, is_test=False)
    assert findings == [], f"{code} good.py should be clean, got {[f.render() for f in findings]}"


def test_structural_checks_are_exempt_in_test_code() -> None:
    # TB001-003 do not fire in test files; TB004 (a test anti-pattern) does.
    for code in ("TB001", "TB002", "TB003"):
        path, source = _fixture(code, "bad")
        assert check_source(path, source, is_test=True) == []
    path, source = _fixture("TB004", "bad")
    produced = {f.code for f in check_source(path, source, is_test=True)}
    assert "TB004" in produced


def test_inline_suppression() -> None:
    source = (
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass  # tessercheck:ignore\n"
        "class Mutable:\n"
        "    x: int\n"
    )
    assert check_source("m.py", source, is_test=False) == []


def test_string_equality_fires_regardless_of_test_scope() -> None:
    src = "def f(a: object, b: object) -> None:\n    assert str(a) == str(b)\n"
    assert {f.code for f in run_source("anywhere.py", src)} == {"TB004"}


def test_setattr_delattr_both_flagged_outside_post_init() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class S:\n"
        "    v: str\n"
        "    def clear(self) -> None:\n"
        "        object.__delattr__(self, 'v')\n"
    )
    assert {f.code for f in check_source("s.py", src, is_test=False)} == {"TB003"}


def test_tb003_spec_init_exemption_covers_only_field_setattr() -> None:
    # The sanctioned site is narrow: __setattr__ of a DECLARED field, inside
    # __init__, of a class declaring BOTH frozen=True and init=False. __delattr__
    # in that same __init__ is still mutation and stays flagged.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Name:\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "        object.__delattr__(self, '_value')\n"
    )
    findings = [f for f in check_source("n.py", src, is_test=False) if f.code == "TB003"]
    assert len(findings) == 1
    assert "__delattr__" in findings[0].message


def test_tb003_spec_init_exemption_requires_enclosing_class() -> None:
    # object.__setattr__ inside a bare module-level function named __init__
    # (no enclosing class) can never be the sanctioned construction write.
    # The preceding spec-init class must not leak its exemption into it either
    # — proves the class-stack pop after Label actually clears the stack.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Label:\n"
        "    _name: str\n"
        "    def __init__(self, name: str) -> None:\n"
        "        object.__setattr__(self, '_name', name)\n"
        "\n"
        "def __init__(self, value):\n"
        "    object.__setattr__(self, '_value', value)\n"
    )
    findings = [f for f in check_source("m.py", src, is_test=False) if f.code == "TB003"]
    assert len(findings) == 1
    assert findings[0].line == 9


def test_tb003_spec_init_exemption_rejects_malformed_setattr_calls() -> None:
    # The exemption's shape check is strict: fewer than 2 args, a non-self
    # target, and a non-string-constant field name are each still mutation,
    # even inside __init__ of a frozen(init=False) class.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=False)\n"
        "class X:\n"
        "    _v: str\n"
        "    def __init__(self, other: 'X', key: str, v: str) -> None:\n"
        "        object.__setattr__(self)\n"
        "        object.__setattr__(other, '_v', v)\n"
        "        object.__setattr__(self, key, v)\n"
        "        object.__setattr__(self, '_v', v)\n"
    )
    findings = [f for f in check_source("m.py", src, is_test=False) if f.code == "TB003"]
    assert [f.line for f in findings] == [6, 7, 8]


def test_tb003_spec_init_shape_detected_past_a_non_dataclass_decorator() -> None:
    # _dataclass_init_false must skip a leading non-dataclass decorator to
    # find the @dataclass(...) one, not bail out on the first mismatch.
    src = (
        "from dataclasses import dataclass\n"
        "\n"
        "def marker(cls):\n"
        "    return cls\n"
        "\n"
        "@marker\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Y:\n"
        "    _v: str\n"
        "    def __init__(self, v: str) -> None:\n"
        "        object.__setattr__(self, '_v', v)\n"
    )
    assert "TB003" not in {f.code for f in check_source("m.py", src, is_test=False)}


def test_tb010_accessor_without_return_annotation_falls_back_to_field_type() -> None:
    # An accessor with no ``->`` annotation is still caught via the backing
    # field's own declared type, not waved through for lack of a type hint.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str\n"
        "    def key(self):\n"
        "        return self._key\n"
    )
    findings = [f for f in check_source("s.py", src, is_test=False) if f.code == "TB010"]
    assert len(findings) == 1


def test_tb010_accessor_suppression() -> None:
    # The inline suppression marker exempts a flagged accessor, same as it
    # does the public-field leak.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str\n"
        "    def key(self) -> str:  # tessercheck:ignore\n"
        "        return self._key\n"
    )
    assert "TB010" not in {f.code for f in check_source("s.py", src, is_test=False)}


def test_tb010_computed_primitive_return_is_not_a_passthrough_accessor() -> None:
    # The accessor ban targets the bare passthrough (return self._x). A method
    # that computes is not handing the wrapped representation back.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def shouted(self) -> str:\n"
        "        return self._value.upper()\n"
    )
    assert "TB010" not in {f.code for f in check_source("s.py", src, is_test=False)}


def test_tb010_accessor_ban_is_a_value_object_rule() -> None:
    # An entity's bool/str state accessor is TB011/TB012 territory, not TB010 —
    # the primitive-escape ban keys on the VALUE_OBJECT stereotype.
    src = (
        "class Link:\n"
        "    def __init__(self, id: str, active: bool) -> None:\n"
        "        self._id = id\n"
        "        self._active = active\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Link) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
        "    @property\n"
        "    def active(self) -> bool:\n"
        "        return self._active\n"
    )
    assert "TB010" not in {f.code for f in check_source("l.py", src, is_test=False)}


def test_tb002_exempts_a_spec_row_collection_field() -> None:
    # TB002 is a value-object rule, keyed on classification. A frozen dataclass
    # that is a spec / persistence row (public primitive fields, no validation)
    # classifies SPEC, not VALUE_OBJECT, so its collection field must NOT trip
    # TB002 — the repo-row false positive the fold removes.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class ReportRow:\n"
        "    id: str\n"
        "    labels: dict[str, str]\n"
    )
    assert check_source("row.py", src, is_test=False) == []


def test_tb014_value_object_must_not_block_equality() -> None:
    # A value object compares by value; __eq__ = None (blocking) is an
    # aggregate's rule, not a VO's.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Amount:\n"
        "    _value: int\n"
        "    __eq__ = None\n"
    )
    assert "TB014" in {f.code for f in check_source("a.py", src, is_test=False)}


def test_tb014_aggregate_root_must_block_equality() -> None:
    # Group embeds the Member entity (a collection of them) → aggregate root; it
    # must block equality with __eq__ = None, not define an __eq__.
    src = (
        "class Member:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Member) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
        "class Group:\n"
        "    def __init__(self, members: list) -> None:\n"
        "        self._members = list(members)\n"
        "    @property\n"
        "    def members(self) -> tuple[Member, ...]:\n"
        "        return tuple(self._members)\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return other is self\n"
        "    def __hash__(self) -> int:\n"
        "        return id(self)\n"
    )
    codes = {f.code for f in check_source("g.py", src, is_test=False)}
    assert "TB014" in codes


def test_tb014_entity_with_paired_eq_hash_is_clean() -> None:
    src = (
        "class Widget:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Widget) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
    )
    assert {f.code for f in check_source("w.py", src, is_test=False)} == set()


def _tb020(source: str) -> list[Finding]:
    return check_comments("f.py", source, ast.parse(source))


def test_tb020_flags_class_and_async_function_docstrings() -> None:
    # The good.py/bad.py fixtures only exercise Module + FunctionDef docstrings.
    # ClassDef and AsyncFunctionDef are separate members of the isinstance tuple;
    # a regression dropping either would ship undetected without this.
    src = (
        "class C:\n"
        '    """class doc"""\n'
        "    x = 1\n"
        "async def g() -> None:\n"
        '    """async doc"""\n'
        "    return None\n"
    )
    findings = _tb020(src)
    assert {f.line for f in findings} == {2, 5}
    assert all(f.code == "TB020" for f in findings)


@pytest.mark.parametrize(
    "comment",
    [
        "# coding: utf-8",
        "# -*- coding: utf-8 -*-",
        "# fmt: off",
        "# isort: skip",
        "# ruff: noqa",
        # tb-* markers are split so a contiguous marker token in this source is
        # not picked up by roadmap/generate.py's marker scan.
        "# tb-" + "cell: value-objects py-example",
        "# tb-" + "status: green",
        "# tb-" + "allow-missing: some/path",
        "# tesser-category: spec",
    ],
)
def test_tb020_directive_ledger_entries_are_exempt(comment: str) -> None:
    # The fixture proves only shebang/noqa/type:/pragma. These remaining ledger
    # entries live inside the directive regex, invisible to branch coverage —
    # dropping an alternation would pass every other test.
    assert _tb020(f"x = 1  {comment}\n") == []


@pytest.mark.parametrize(
    "comment",
    ["# tesser-category: spce", "# tesser-category:", "# tesser-category: dtoo"],
)
def test_tb020_exempts_a_malformed_category_marker_too(comment: str) -> None:
    # The exemption is on the PREFIX, deliberately. A typo'd or empty category
    # is TB032's finding to report; if TB020 also fired, the author would be
    # told they wrote a banned comment when what they wrote was a misspelled
    # directive — and the comments-norm diagnosis is the misleading one.
    assert _tb020(f"x = 1  {comment}\n") == []


def test_tb020_trailing_marker_suppresses_comment_and_docstring() -> None:
    # A real comment and a real docstring, each on a line carrying the
    # `# tessercheck:ignore` marker, are suppressed (the `suppressed` branch in
    # both loops).
    assert _tb020("x = 1  # real prose  # tessercheck:ignore\n") == []
    assert (
        _tb020('def f() -> None:\n    """doc"""  # tessercheck:ignore\n    return None\n')
        == []
    )


def test_tb020_tokenize_error_is_loud_and_docstring_check_still_runs() -> None:
    # tokenize and ast do not share a lexer; a source that ast accepts can
    # still raise TokenError. The failure must be LOUD (a finding, not a
    # silently comment-blind pass) and the docstring pass must still run.
    tree = ast.parse('"""module doc"""\n')
    findings = check_comments("f.py", "(", tree)
    assert [f.code for f in findings] == ["TB020", "TB020"]
    assert "could not be tokenized" in findings[0].message
    assert "docstring" in findings[1].message


def test_tb020_coding_word_beyond_line_two_is_flagged() -> None:
    # The coding exemption is anchored to lines 1-2 (PEP 263). A comment merely
    # containing "coding" further down is prose and must be flagged — an
    # unanchored exemption previously let it escape. bad.py exercises this line,
    # but the meta-test only pins the code *set*, so this locks the specific
    # flag; the line-1 exempt direction is covered by the directive-ledger test.
    src = "x = 1\ny = 2\n# hardcoding=1 is a workaround, not a coding decl\n"
    findings = _tb020(src)
    assert [(f.line, f.code) for f in findings] == [(3, "TB020")]


def test_tb020_bare_string_statement_is_flagged_distinctly_from_docstring() -> None:
    # A string-literal statement mid-body is prose smuggled as a string; it is
    # flagged with the bare-string message, distinct from the docstring message
    # a leading string in a def/class/module gets.
    bare = _tb020('def f() -> None:\n    x = 1\n    "smuggled prose"\n    return None\n')
    assert [f.line for f in bare] == [3]
    assert "bare string-literal" in bare[0].message
    doc = _tb020('"""module doc"""\n')
    assert "docstring" in doc[0].message


def test_tb010_alias_passthrough_is_still_a_passthrough() -> None:
    # `v = self._x; return v` is the direct passthrough in a one-line disguise;
    # the adversarial pass showed it slipped the accessor ban entirely.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str\n"
        "    def key(self) -> str:\n"
        "        v = self._key\n"
        "        return v\n"
    )
    findings = [f for f in check_source("s.py", src, is_test=False) if f.code == "TB010"]
    assert len(findings) == 1


def test_tb011_alias_passthrough_leaks_the_backing_collection() -> None:
    # The alias peel applies to the shared helper, so the aggregate
    # collection-leak check catches `v = self._items; return v` too.
    src = (
        "class Cart:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "        self._items: list = []\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Cart) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
        "    def items(self) -> list:\n"
        "        v = self._items\n"
        "        return v\n"
    )
    assert "TB011" in {f.code for f in check_source("c.py", src, is_test=False)}


def test_tb010_private_helper_accessor_is_exempt() -> None:
    # A `_`-prefixed helper is internal plumbing, matching the field check's
    # underscore exemption — the ban is on the public read surface.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def _raw(self) -> str:\n"
        "        return self._value\n"
    )
    assert "TB010" not in {f.code for f in check_source("s.py", src, is_test=False)}


def test_tb010_optional_primitive_is_not_an_escape_hatch() -> None:
    # `str | None` and Optional[str] contain the banned primitive; a union
    # wrapper must not wave the passthrough accessor (or a public field)
    # through — the Codex structured pass caught this gap.
    src = (
        "from dataclasses import dataclass\n"
        "from typing import Optional\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str | None\n"
        "    _alt: Optional[str] = None\n"
        "    def key(self) -> str | None:\n"
        "        return self._key\n"
        "    def alt(self):\n"
        "        return self._alt\n"
    )
    findings = [f for f in check_source("s.py", src, is_test=False) if f.code == "TB010"]
    assert len(findings) == 2


def test_tb003_truthy_falsy_dataclass_flags_match_runtime_semantics() -> None:
    # dataclasses treat frozen/init by truthiness at runtime: init=0 suppresses
    # __init__ exactly like init=False, so the spec-init exemption honors it;
    # frozen=1 freezes, so TB001 stays quiet.
    spec_init = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=0)\n"
        "class Name:\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
    )
    assert "TB003" not in {f.code for f in check_source("n.py", spec_init, is_test=False)}
    frozen_truthy = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=1)\n"
        "class Row:\n"
        "    x: int\n"
    )
    assert "TB001" not in {f.code for f in check_source("r.py", frozen_truthy, is_test=False)}


def test_tb003_lambda_inside_spec_init_never_inherits_the_exemption() -> None:
    # A lambda defined in __init__ runs POST-construction; a setattr in its
    # body is deferred mutation, not a construction write (adversarial
    # round 2: the lambda body previously saw __init__ as the innermost
    # frame and slipped through).
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Name:\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "        f = lambda v: object.__setattr__(self, '_value', v)\n"
        "        f(value)\n"
    )
    findings = [f for f in check_source("n.py", src, is_test=False) if f.code == "TB003"]
    assert [f.line for f in findings] == [7]


def test_tb003_nested_def_named_init_never_inherits_the_exemption() -> None:
    # The exemption is pinned to the DIRECT class-body __init__ by frame
    # depth; a nested def that happens to be named __init__ is an ordinary
    # inner function and stays flagged.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Name:\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "        def __init__(v: str) -> None:\n"
        "            object.__setattr__(self, '_value', v)\n"
        "        __init__(value)\n"
    )
    findings = [f for f in check_source("n.py", src, is_test=False) if f.code == "TB003"]
    assert [f.line for f in findings] == [8]


def _tb030(src: str, is_test: bool = False) -> set[str]:
    return {f.code for f in check_source("t.py", src, is_test=is_test)}


def test_tb030_bans_every_unittest_mock_import_shape() -> None:
    # from unittest.mock import X ; import unittest.mock ; import unittest.mock as m ;
    # from unittest import mock — each brings a mocking library into the file.
    for src in (
        "from unittest.mock import MagicMock\n",
        "from unittest.mock import patch, AsyncMock\n",
        "import unittest.mock\n",
        "import unittest.mock as m\n",
        "from unittest import mock\n",
    ):
        assert "TB030" in _tb030(src), src


def test_tb030_bans_the_mock_backport() -> None:
    assert "TB030" in _tb030("import mock\n")
    assert "TB030" in _tb030("from mock import MagicMock\n")


def test_tb030_catches_the_import_unittest_evasion() -> None:
    # ``import unittest`` is legitimate (TestCase); the ban is on reaching
    # ``unittest.mock`` through it.
    src = "import unittest\n\n\ndef f() -> object:\n    return unittest.mock.patch('x')\n"
    assert "TB030" in _tb030(src)


def test_tb030_plain_import_unittest_alone_is_not_flagged() -> None:
    assert "TB030" not in _tb030("import unittest\n")


def test_tb030_bans_monkeypatch_in_every_shape() -> None:
    # pytest.MonkeyPatch ; from pytest import MonkeyPatch (which is how a
    # MonkeyPatch().context() use gets the name) ; and the monkeypatch fixture
    # parameter. The name cannot enter a module any other way.
    assert "TB030" in _tb030("import pytest\n\n\ndef f() -> object:\n    return pytest.MonkeyPatch()\n")
    assert "TB030" in _tb030("from pytest import MonkeyPatch\n")
    assert "TB030" in _tb030(
        "from pytest import MonkeyPatch\n"
        "\n"
        "\n"
        "def f() -> None:\n"
        "    with MonkeyPatch().context():\n"
        "        pass\n"
    )
    assert "TB030" in _tb030("def test_x(monkeypatch: object) -> None:\n    monkeypatch.setenv('A', 'B')\n")


def test_tb030_bans_the_mocker_fixture_parameter() -> None:
    # pytest-mock injects its patcher as a fixture named ``mocker``.
    assert "TB030" in _tb030("def test_x(mocker: object) -> None:\n    mocker.patch('a.b')\n")


def test_tb030_fires_regardless_of_test_scope() -> None:
    # Global scope: the fakes-only norm has no test exemption — domain and
    # adapter code have no business importing a mock library either.
    src = "from unittest.mock import MagicMock\n"
    assert "TB030" in _tb030(src, is_test=True)
    assert "TB030" in _tb030(src, is_test=False)


def test_tb030_inline_suppression_clears_a_wiring_patch() -> None:
    # A wiring test that must patch a process seam declares it. Assert the
    # WHOLE finding list is empty, not just that TB030 is absent: the marker is
    # itself a comment, so the hatch is only usable while TB020 also treats it
    # as a directive. A weaker assertion would still pass if TB020 started
    # firing on the marker line and made the hatch unusable.
    clean = "def test_boot(monkeypatch: object) -> None:  # tessercheck:ignore\n    pass\n"
    assert check_source("t.py", clean, is_test=False) == []
    dirty = "def test_boot(monkeypatch: object) -> None:\n    pass\n"
    assert "TB030" in _tb030(dirty)


def test_tb030_suppression_covers_a_formatter_wrapped_import() -> None:
    # The finding reports at the statement's START line, so suppression scans
    # the node's whole span — otherwise a marker on the closing paren of a
    # wrapped import (what a formatter produces) would suppress nothing.
    wrapped = "from unittest.mock import (\n    MagicMock,\n)  # tessercheck:ignore\n"
    assert "TB030" not in _tb030(wrapped)
    assert "TB030" in _tb030("from unittest.mock import (\n    MagicMock,\n)\n")


def test_tb030_reports_one_finding_per_violation() -> None:
    # An import plus N uses of the imported name is ONE violation with one
    # place to fix. There is no bare-Name arm, so the import is reported once
    # and a single suppression marker can clear it — rather than one finding
    # per reference, each needing its own marker.
    src = (
        "from pytest import MonkeyPatch\n"
        "\n"
        "\n"
        "def f(mp: MonkeyPatch) -> object:\n"
        "    with MonkeyPatch().context() as m:\n"
        "        return m\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=True) if f.code == "TB030"]
    assert [f.line for f in findings] == [1]


def test_tb030_fixture_param_scan_does_not_fire_on_production_code() -> None:
    # The identifier-name signal is scoped to pytest-shaped functions. A
    # production function that happens to take a parameter named monkeypatch or
    # mocker is an ordinary name, not a fixture injection — flagging it would
    # redden conformant code.
    prod = "def configure(mocker: object, monkeypatch: object) -> None:\n    pass\n"
    assert "TB030" not in _tb030(prod)
    # ...but a fixture factory and a test function both count as pytest-shaped.
    assert "TB030" in _tb030(
        "import pytest\n"
        "\n"
        "\n"
        "@pytest.fixture\n"
        "def thing(monkeypatch: object) -> object:\n"
        "    return monkeypatch\n"
    )


def test_tb030_detects_positional_only_and_keyword_only_fixture_params() -> None:
    # The fixture-param scan covers all three arg lists. Without posonlyargs
    # and kwonlyargs in the tuple these two shapes slip through silently.
    assert "TB030" in _tb030("def test_x(monkeypatch: object, /) -> None:\n    pass\n")
    assert "TB030" in _tb030("def test_x(*, mocker: object) -> None:\n    pass\n")


def test_tb030_detects_an_async_test_function() -> None:
    # AsyncFunctionDef is a separate node type; dropping it from the isinstance
    # tuple would be a silent no-op for a suite of sync-only tests.
    src = "async def test_x(mocker: object) -> None:\n    pass\n"
    assert "TB030" in _tb030(src)


def test_tb030_finding_points_at_the_argument_not_the_def() -> None:
    # emit(arg, ...) is deliberate: the finding locates the offending fixture
    # parameter, not the enclosing def. Locking the payload (line, col, message)
    # so the choice can't silently regress to the statement position.
    src = "def test_x(monkeypatch: object) -> None:\n    pass\n"
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB030"]
    assert len(findings) == 1
    assert findings[0].line == 1
    assert findings[0].col == src.index("monkeypatch") + 1
    assert "monkeypatch" in findings[0].message


def test_tb030_suppression_applies_to_an_import_shape() -> None:
    # Suppression keys on the line the finding is emitted at, which for an
    # import is the statement's FIRST line — the marker must sit there.
    assert "TB030" not in _tb030(
        "from unittest.mock import MagicMock  # tessercheck:ignore\n"
    )
    assert "TB030" in _tb030("from unittest.mock import MagicMock\n")


def test_tb030_matches_submodules_of_a_banned_module() -> None:
    # Exact-string matching let real submodules through: mock.mock is a genuine
    # module of the PyPI backport that re-exports patch/MagicMock.
    assert "TB030" in _tb030("import mock.mock\n")
    assert "TB030" in _tb030("from mock.mock import patch\n")
    assert "TB030" in _tb030("import unittest.mock.mock\n")
    # A module that merely starts with the same letters is not a submodule.
    assert "TB030" not in _tb030("import mockingbird\n")
    assert "TB030" not in _tb030("from mockingbird import Song\n")


def test_tb030_marker_must_be_a_real_comment_not_a_string_literal() -> None:
    # Substring-scanning the raw line let a string literal that merely CONTAINS
    # the marker text suppress a real violation — a review-invisible bypass.
    # Suppression now keys on an actual COMMENT token.
    spoof = "SRC = '# tessercheck:ignore'\nfrom unittest.mock import patch\n"
    assert "TB030" in _tb030(spoof)
    real = "from unittest.mock import patch  # tessercheck:ignore\n"
    assert "TB030" not in _tb030(real)


def test_tb030_catches_monkeypatch_from_its_private_home() -> None:
    # MonkeyPatch's real definition lives in _pytest.monkeypatch; importing it
    # from there is the same violation as importing it from pytest.
    assert "TB030" in _tb030("from _pytest.monkeypatch import MonkeyPatch\n")


def test_tb030_leaves_a_hand_written_fake_alone() -> None:
    src = (
        "class FakeSender:\n"
        "    def __init__(self) -> None:\n"
        "        self._sent: list[str] = []\n"
        "    def send(self, to: str) -> None:\n"
        "        self._sent.append(to)\n"
    )
    assert "TB030" not in _tb030(src)


def test_tb003_classvar_is_not_a_sanctioned_setattr_target() -> None:
    # ClassVar/InitVar annotations are not dataclass instance fields, so
    # writing one via object.__setattr__ in the spec-init is not the
    # sanctioned construction write.
    src = (
        "from dataclasses import dataclass\n"
        "from typing import ClassVar\n"
        "@dataclass(frozen=True, init=False)\n"
        "class Name:\n"
        "    _value: str\n"
        "    _registry: ClassVar[str] = ''\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "        object.__setattr__(self, '_registry', value)\n"
    )
    findings = [f for f in check_source("n.py", src, is_test=False) if f.code == "TB003"]
    assert [f.line for f in findings] == [9]


def test_tb010_annotated_alias_passthrough_is_still_a_passthrough() -> None:
    # `v: str = self._x; return v` — the typed-code spelling of the alias
    # disguise — is peeled the same as the bare assignment.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str\n"
        "    def key(self) -> str:\n"
        "        v: str = self._key\n"
        "        return v\n"
    )
    findings = [f for f in check_source("s.py", src, is_test=False) if f.code == "TB010"]
    assert len(findings) == 1


def test_tb003_hand_written_init_without_init_false_declaration_stays_flagged() -> None:
    # The exemption requires the DECLARED shape. A frozen dataclass with a
    # hand-written __init__ but no init=False keyword is nudged to declare it —
    # a dedicated lock so a future broadening of the exemption cannot slip
    # past the set-only fixture assertion.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Code:\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
    )
    assert "TB003" in {f.code for f in check_source("c.py", src, is_test=False)}


def _codes(src: str) -> set[str]:
    return {f.code for f in check_source("t.py", src, is_test=False)}


_LEAF = (
    "from dataclasses import dataclass\n"
    "@dataclass(frozen=True)\n"
    "class Slug:\n"
    "    _value: str\n"
)


def test_tb015_leaf_with_its_one_matching_exit_is_clean() -> None:
    assert "TB015" not in _codes(_LEAF + "    def __str__(self) -> str:\n        return self._value\n")


def test_tb015_leaf_with_no_exit_at_all_is_not_flagged() -> None:
    # The check bans the wrong door, not the absence of one — a leaf with no
    # canonical exit is a different (unruled) question.
    assert "TB015" not in _codes(_LEAF)


def test_tb015_flags_a_mismatched_exit_on_a_leaf() -> None:
    src = _LEAF + "    def __int__(self) -> int:\n        return int(self._value)\n"
    assert "TB015" in _codes(src)


def test_tb015_flags_a_second_exit_on_a_leaf() -> None:
    src = (
        _LEAF
        + "    def __str__(self) -> str:\n        return self._value\n"
        + "    def __bytes__(self) -> bytes:\n        return self._value.encode()\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB015"]
    assert len(findings) == 1
    assert "__bytes__" in findings[0].message


def test_tb015_decimal_and_datetime_leaves_exit_as_canonical_text() -> None:
    for imp, typ in (("from decimal import Decimal", "Decimal"), ("from datetime import datetime", "datetime")):
        src = (
            f"{imp}\nfrom dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class V:\n"
            f"    _value: {typ}\n"
            "    def __str__(self) -> str:\n        return str(self._value)\n"
        )
        assert "TB015" not in _codes(src), typ


def test_tb015_flags_any_dunder_on_a_collection_value_object() -> None:
    # A collection VO is structured: Labels lost its joined __str__ under the
    # 2026-07-20 zero-dunder ruling.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Label:\n"
        "    _value: str\n"
        "    def __str__(self) -> str:\n        return self._value\n"
        "@dataclass(frozen=True)\n"
        "class Labels:\n"
        "    _values: tuple[Label, ...]\n"
        "    def __str__(self) -> str:\n        return ','.join(str(v) for v in self._values)\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB015"]
    assert len(findings) == 1
    assert "Labels" in findings[0].message


def test_tb015_private_spec_returning_helper_is_out_of_scope() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class SlugSpec:\n"
        "    value: str\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def _to_spec(self) -> SlugSpec:\n        return SlugSpec(value=self._value)\n"
    )
    assert "TB015" not in _codes(src)


def test_tb015_emit_requires_the_sink_to_be_a_parameter() -> None:
    # A method calling a helper with its own state is not the emit-a-sink shape;
    # the sink must be something the caller handed in.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def register(self) -> None:\n        _LOG.append(self._value)\n"
    )
    assert "TB015" not in _codes(src)


def test_tb015_is_suppressible_inline() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def __int__(self) -> int:  # tessercheck:ignore\n        return int(self._value)\n"
    )
    assert "TB015" not in _codes(src)


def test_tb016_leaves_a_single_field_leaf_alone() -> None:
    assert "TB016" not in _codes(_LEAF)


def test_tb016_flags_every_bare_primitive_in_a_compound() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Point:\n"
        "    _x: float\n"
        "    _y: float\n"
        "    def __post_init__(self) -> None:\n        pass\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB016"]
    assert len(findings) == 2


def test_tb016_is_clean_when_components_are_value_objects() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class X:\n"
        "    _value: float\n"
        "    def __float__(self) -> float:\n        return self._value\n"
        "@dataclass(frozen=True)\n"
        "class Point:\n"
        "    _x: X\n"
        "    _y: X\n"
        "    def __post_init__(self) -> None:\n        pass\n"
    )
    assert "TB016" not in _codes(src)


def test_tb016_does_not_fire_on_a_spec() -> None:
    # A spec is the one sanctioned primitive bag — it exposes by design.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class MoneySpec:\n"
        "    amount: str\n"
        "    currency: str\n"
    )
    assert "TB016" not in _codes(src)


def test_tb016_is_suppressible_inline() -> None:
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Point:\n"
        "    _x: float  # tessercheck:ignore\n"
        "    _y: float  # tessercheck:ignore\n"
        "    def __post_init__(self) -> None:\n        pass\n"
    )
    assert "TB016" not in _codes(src)


def test_tb015_leaf_backed_by_an_unruled_scalar_is_not_mistaken_for_structured() -> None:
    # A date-backed leaf with its canonical-text exit is a LEAF, not a compound.
    # date has no ruled canonical exit yet, so its __str__ is out of contract
    # and left alone — never flagged as a structured-type dunder.
    src = (
        "from datetime import date\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Day:\n"
        "    _value: date\n"
        "    def __post_init__(self) -> None:\n        pass\n"
        "    def __str__(self) -> str:\n        return self._value.isoformat()\n"
    )
    assert "TB015" not in _codes(src)


def test_tb016_flags_a_compound_holding_a_raw_date() -> None:
    # The 2026-07-20 collapse: date/datetime/time joined the must-wrap set.
    src = (
        "from datetime import date\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Window:\n"
        "    _start: date\n"
        "    _end: date\n"
        "    def __post_init__(self) -> None:\n        pass\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB016"]
    assert len(findings) == 2


def test_tb010_flags_an_accessor_returning_a_raw_date() -> None:
    src = (
        "from datetime import date\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Day:\n"
        "    _value: date\n"
        "    def __post_init__(self) -> None:\n        pass\n"
        "    @property\n"
        "    def value(self) -> date:\n        return self._value\n"
    )
    assert "TB010" in _codes(src)


def test_tb015_checks_a_date_leaf_exit_now_that_date_is_ruled() -> None:
    # date exits as canonical text via __str__; __int__ is a mismatch.
    good = (
        "from datetime import date\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Day:\n"
        "    _value: date\n"
        "    def __post_init__(self) -> None:\n        pass\n"
        "    def __str__(self) -> str:\n        return self._value.isoformat()\n"
    )
    assert "TB015" not in _codes(good)
    bad = good.replace(
        "    def __str__(self) -> str:\n        return self._value.isoformat()\n",
        "    def __int__(self) -> int:\n        return self._value.toordinal()\n",
    )
    assert "TB015" in _codes(bad)


def test_a_bool_leaf_is_flagged_by_tb016_not_tb015() -> None:
    # bool is not value-object material (2026-07-20 ruling): wrapping one is the
    # violation, owned by TB016. TB015 stays silent — the exit is not the issue.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Flag:\n"
        "    _value: bool\n"
        "    def __post_init__(self) -> None:\n        pass\n"
        "    def __str__(self) -> str:\n        return 'yes' if self._value else 'no'\n"
    )
    codes = _codes(src)
    assert "TB016" in codes
    assert "TB015" not in codes


def test_tb016_flags_a_bool_leaf_and_a_complex_leaf() -> None:
    for typ in ("bool", "complex"):
        src = (
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class Wrapper:\n"
            f"    _value: {typ}\n"
            "    def __post_init__(self) -> None:\n        pass\n"
        )
        assert "TB016" in _codes(src), typ


def test_tb016_flags_a_bool_field_inside_a_compound_vo() -> None:
    # A bool has no legal home in a value object: it cannot be raw (rule 5) and
    # cannot be wrapped (not VO material). Flagged wherever it sits in a VO.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Amount:\n"
        "    _value: str\n"
        "    def __str__(self) -> str:\n        return self._value\n"
        "@dataclass(frozen=True)\n"
        "class Money:\n"
        "    _amount: Amount\n"
        "    _estimate: bool\n"
        "    def __post_init__(self) -> None:\n        pass\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB016"]
    assert len(findings) == 1
    assert "_estimate" in findings[0].message


def test_tb016_leaves_an_entity_bool_field_alone() -> None:
    # TB016 is value-object-scoped; an entity holds raw primitives as state.
    src = (
        "class Link:\n"
        "    def __init__(self, id: str, active: bool) -> None:\n"
        "        self._id = id\n"
        "        self._active = active\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Link) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n        return hash(self._id)\n"
    )
    assert "TB016" not in _codes(src)


def test_tb017_flags_a_classmethod_factory_returning_its_own_type() -> None:
    src = _LEAF + (
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> 'Slug':\n        return cls(raw.strip())\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB017"]
    assert len(findings) == 1
    assert "parse" in findings[0].message


def test_tb017_flags_a_staticmethod_factory_too() -> None:
    # Spelled without cls, it is the same second door.
    src = _LEAF + (
        "    @staticmethod\n"
        "    def of(raw: str) -> 'Slug':\n        return Slug(raw)\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_sees_through_self_and_wrapped_return_annotations() -> None:
    for ann in ("'Slug'", "Slug", "Self", "'Slug | None'", "Optional['Slug']"):
        src = _LEAF + (
            "    @classmethod\n"
            f"    def make(cls, raw: str) -> {ann}:\n        return cls(raw)\n"
        )
        assert "TB017" in _codes(src), ann


def test_tb017_leaves_a_factory_returning_another_type_alone() -> None:
    # Not a construction door: it builds something else. The ban is on second
    # ways to build THIS type.
    src = _LEAF + (
        "    @classmethod\n"
        "    def field_names(cls) -> tuple[str, ...]:\n        return ('_value',)\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_leaves_a_spec_factory_alone() -> None:
    # A spec is an inert primitive carrier, not a value object — building one
    # from a row is the inbound door's own business.
    src = (
        "from dataclasses import dataclass\n"
        "from collections.abc import Mapping\n"
        "@dataclass(frozen=True)\n"
        "class SlugSpec:\n"
        "    value: str\n"
        "    @classmethod\n"
        "    def from_row(cls, row: Mapping[str, str]) -> 'SlugSpec':\n"
        "        return cls(value=row['value'])\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_leaves_entities_to_tb013() -> None:
    # TB013 owns identity objects and is deliberately narrower (the from_spec
    # name only); TB017 must not widen that mandate by the back door.
    src = (
        "class Widget:\n"
        "    def __init__(self, id: str) -> None:\n        self._id = id\n"
        "    @classmethod\n"
        "    def restore(cls, id: str) -> 'Widget':\n        return cls(id)\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Widget) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n        return hash(self._id)\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_is_suppressible() -> None:
    src = _LEAF + (
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> 'Slug':  # tessercheck:ignore\n"
        "        return cls(raw)\n"
    )
    assert "TB017" not in _codes(src)


_ROUTED = (
    "from dataclasses import dataclass\n"
    "from serialization import canonical_str\n"
    "@dataclass(frozen=True)\n"
    "class Slug:\n"
    "    _value: str\n"
)


def test_tb018_clean_when_the_exit_delegates_to_its_policy_helper() -> None:
    src = _ROUTED + "    def __str__(self) -> str:\n        return canonical_str(self._value)\n"
    assert "TB018" not in _codes(src)


def test_tb018_flags_a_hand_rolled_exit() -> None:
    for body in ("self._value", "str(self._value)", "self._value.strip()"):
        src = _ROUTED + f"    def __str__(self) -> str:\n        return {body}\n"
        findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB018"]
        assert len(findings) == 1, body
        assert "canonical_str" in findings[0].message


def test_tb018_flags_delegation_to_the_wrong_policy() -> None:
    # A Decimal leaf routed through str's identity gets a form nothing else
    # in the system agrees on.
    src = (
        "from decimal import Decimal\nfrom dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Price:\n"
        "    _value: Decimal\n"
        "    def __str__(self) -> str:\n        return canonical_str(str(self._value))\n"
    )
    findings = [f for f in check_source("t.py", src, is_test=False) if f.code == "TB018"]
    assert len(findings) == 1
    assert "canonical_decimal" in findings[0].message


def test_tb018_flags_a_post_processed_helper_result() -> None:
    # The helper's output is the canonical form; anything applied after it is a
    # second author of the same form.
    src = _ROUTED + (
        "    def __str__(self) -> str:\n        return canonical_str(self._value).upper()\n"
    )
    assert "TB018" in _codes(src)


def test_tb018_leaves_date_and_time_leaves_out_of_contract() -> None:
    # A ruled exit (__str__) but no ruled canonical FORM yet — the time-type
    # taxonomy is open (TODOS.md). Out of contract beats guessed at.
    for imp, typ in (("from datetime import date", "date"), ("from datetime import time", "time")):
        src = (
            f"{imp}\nfrom dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class V:\n"
            f"    _value: {typ}\n"
            "    def __str__(self) -> str:\n        return self._value.isoformat()\n"
        )
        assert "TB018" not in _codes(src), typ


def test_tb018_leaves_the_mismatched_dunder_shape_to_tb015() -> None:
    # A str-backed leaf defining __int__ is one violation, and it is TB015's.
    src = _ROUTED + "    def __int__(self) -> int:\n        return int(self._value)\n"
    codes = _codes(src)
    assert "TB015" in codes
    assert "TB018" not in codes


def test_tb018_is_suppressible() -> None:
    src = _ROUTED + (
        "    def __str__(self) -> str:  # tessercheck:ignore\n        return self._value\n"
    )
    assert "TB018" not in _codes(src)


def test_tb018_flags_an_exit_that_is_not_one_line() -> None:
    # The contract is a one-LINE delegation: the policy helper's output is the
    # canonical form, so a body with room for a second statement has room for a
    # second author.
    src = _ROUTED + (
        "    def __str__(self) -> str:\n"
        "        v = canonical_str(self._value)\n        return v\n"
    )
    assert "TB018" in _codes(src)


def test_tb018_flags_an_exit_that_never_delegates() -> None:
    src = _ROUTED + "    def __str__(self) -> str:\n        raise ValueError('x')\n"
    assert "TB018" in _codes(src)


def test_tb017_sees_a_qualified_own_type_annotation() -> None:
    # typing.Self and a module-qualified own type are Attribute nodes, not Name.
    for ann in ("typing.Self", "mod.Slug"):
        src = _LEAF + (
            "    @classmethod\n"
            f"    def make(cls, raw: str) -> {ann}:\n        return cls(raw)\n"
        )
        assert "TB017" in _codes(src), ann


def test_tb017_ignores_a_non_factory_decorator() -> None:
    # Only classmethod/staticmethod make a method reachable without an instance;
    # an arbitrary decorator on an instance method is not a door.
    src = _LEAF + (
        "    @some.deco(1)\n"
        "    def make(self, raw: str) -> 'Slug':\n        return Slug(raw)\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_is_conservative_about_an_unparseable_string_annotation() -> None:
    # A string annotation is never compiled by Python, so it can hold anything.
    # The resolver must neither crash nor guess. Body is non-constructing here
    # so the annotation path is what is under test.
    src = _LEAF + (
        "    @classmethod\n"
        "    def make(cls, raw: str) -> 'not valid!!':\n        return tuple(raw)\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_body_wins_when_the_annotation_is_unresolvable() -> None:
    # Garbage annotation, constructing body: the body is the truth.
    src = _LEAF + (
        "    @classmethod\n"
        "    def make(cls, raw: str) -> 'not valid!!':\n        return cls(raw)\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_catches_an_unannotated_factory_by_its_body() -> None:
    # The return annotation is optional Python. A tree without a strict type
    # checker would otherwise hide the same second door.
    src = _LEAF + (
        "    @classmethod\n    def coerce(cls, raw):\n        return cls(raw)\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_body_detection_does_not_fire_on_a_non_constructing_factory() -> None:
    # Returns a call, but not to its own type — still not a door.
    src = _LEAF + (
        "    @classmethod\n    def parse_all(cls, raws):\n        return tuple(raws)\n"
    )
    assert "TB017" not in _codes(src)


def test_tb017_catches_construction_regardless_of_return_statement_shape() -> None:
    # The return statement is the easiest thing to vary; construction is not.
    bodies = (
        "        v = cls(raw)\n        return v\n",
        "        return cls(raw) if raw else cls('x')\n",
        "        return (out := cls(raw))\n",
        "        return mod.Slug(raw)\n",
    )
    for body in bodies:
        src = _LEAF + f"    @classmethod\n    def parse(cls, raw):\n{body}"
        assert "TB017" in _codes(src), body


def test_tb017_catches_the_new_bypass_that_skips_init_entirely() -> None:
    # object.__new__(cls) is the door that matters most: it constructs without
    # running __init__, so every invariant the one door enforces is skipped.
    src = _LEAF + (
        "    @classmethod\n    def raw(cls, v):\n"
        "        o = object.__new__(cls)\n"
        "        object.__setattr__(o, '_value', v)\n        return o\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_trusts_an_annotation_that_names_another_type() -> None:
    # Builds its own type internally on the way to an int — not a door. The
    # body is consulted only when the annotation says nothing trustworthy.
    src = _LEAF + (
        "    @classmethod\n    def count(cls, raws) -> int:\n"
        "        return sum(1 for r in raws if cls(r))\n"
    )
    assert "TB017" not in _codes(src)


def test_tb018_accepts_a_module_qualified_helper_call() -> None:
    # from-import and module-qualified are the same delegation; the check must
    # not push authors toward one spelling.
    src = (
        "from dataclasses import dataclass\nimport serialization\n"
        "@dataclass(frozen=True)\nclass S:\n    _value: str\n"
        "    def __str__(self) -> str:\n"
        "        return serialization.canonical_str(self._value)\n"
    )
    assert "TB018" not in _codes(src)


def test_tb018_flags_a_pre_processed_helper_argument() -> None:
    # Post-processing was already flagged; pre-processing is the same second
    # author applied one step earlier.
    src = _ROUTED + (
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value.upper())\n"
    )
    assert "TB018" in _codes(src)


_SPEC_DEF = (
    "from dataclasses import dataclass\n"
    "@dataclass(frozen=True)\n"
    "class LinkSpec:\n"
    "    slug: str\n"
)


def _tb032(src: str, is_test: bool = False) -> list[Finding]:
    return [f for f in check_source("t.py", src, is_test=is_test) if f.code == "TB032"]


def test_tb032_judges_a_module_whose_tests_live_on_a_class() -> None:
    # The reason detection WALKS instead of scanning tree.body. pytest's class
    # style puts every test on a Test* class, so a module-level scan sees no
    # tests, exempts the whole file, and takes its helpers with it.
    # examples/python/tests/test_short_link.py is exactly this shape.
    src = (
        "def _detect(x: int) -> int:\n"
        "    return x\n"
        "class TestThing:\n"
        "    def test_it(self) -> None:\n"
        "        assert _detect(1) == 1\n"
    )
    assert [f.line for f in _tb032(src)] == [1]


def test_tb032_is_silent_in_a_module_that_defines_no_test() -> None:
    # The known hole, locked deliberately rather than left to drift: a
    # helper-only module beside the tests is never judged. Closing it means
    # deciding what makes a non-test module part of the test tree.
    src = "def json_request(body: str) -> bytes:\n    return body.encode()\n"
    assert _tb032(src) == []
    # ...and the is_test FLAG must not be what turns the check on, or the
    # bad.py fixture (checked with is_test=False) could not prove it.
    assert _tb032(src, is_test=True) == []


def test_tb032_leaves_the_methods_of_a_fake_alone() -> None:
    # Every non-test method on a class in the two gated example trees is a
    # hand-written fake implementing a collaborator's interface — the shape
    # TB030 REQUIRES. Judging methods would report the norm's own mandated
    # construct as a violation.
    src = (
        "class FakeRepo:\n"
        "    def __init__(self) -> None:\n"
        "        self.saved: list[str] = []\n"
        "    def save(self, x: str) -> None:\n"
        "        self.saved.append(x)\n"
        "def test_it() -> None:\n"
        "    FakeRepo().save('x')\n"
    )
    assert _tb032(src) == []


def test_tb032_leaves_a_function_nested_inside_a_test_alone() -> None:
    # A closure inside a test is local to it, not a shared helper.
    src = (
        "def test_it() -> None:\n"
        "    def inner(x: int) -> int:\n"
        "        return x\n"
        "    assert inner(1) == 1\n"
    )
    assert _tb032(src) == []


def test_tb032_accepts_a_spec_returning_helper_declared_in_the_file() -> None:
    # The shared registry excludes test files so a fake cannot shadow a domain
    # type tree-wide. That is a rule about shadowing, not a reason to deny this
    # check local knowledge: a helper returning a spec is conformant wherever
    # the spec is declared.
    src = _SPEC_DEF + (
        "def _spec(slug: str = 'a') -> LinkSpec:\n"
        "    return LinkSpec(slug=slug)\n"
        "def test_it() -> None:\n"
        "    assert _spec().slug == 'a'\n"
    )
    assert _tb032(src) == []


def test_tb032_accepts_a_spec_inside_a_collection_annotation() -> None:
    src = _SPEC_DEF + (
        "def _specs(n: int = 1) -> tuple[LinkSpec, ...]:\n"
        "    return tuple(LinkSpec(slug='a') for _ in range(n))\n"
        "def test_it() -> None:\n"
        "    assert len(_specs()) == 1\n"
    )
    assert _tb032(src) == []


@pytest.mark.parametrize(
    "decorator", ["@pytest.fixture", "@pytest.fixture()", "@fixture", "@fixture()"]
)
def test_tb032_accepts_a_fixture_in_every_decorator_shape(decorator: str) -> None:
    src = (
        f"{decorator}\n"
        "def base_url() -> str:\n"
        "    return 'http://127.0.0.1'\n"
        "def test_it(base_url: str) -> None:\n"
        "    assert base_url\n"
    )
    assert _tb032(src) == []


def test_tb032_judges_an_async_helper() -> None:
    # An AsyncFunctionDef is a definition like any other; a FunctionDef-only
    # walk would exempt it, and there are zero in-tree instances to catch that.
    src = (
        "async def _fetch(url: str) -> bytes:\n"
        "    return url.encode()\n"
        "def test_it() -> None:\n"
        "    assert _fetch\n"
    )
    assert [f.line for f in _tb032(src)] == [1]


def test_tb032_marker_attaches_from_the_line_above_and_from_the_def_line() -> None:
    above = (
        "# tesser-category: dto\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    trailing = (
        "def _view() -> dict[str, str]:  # tesser-category: dto\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    assert _tb032(above) == []
    assert _tb032(trailing) == []


def test_tb032_marker_reaches_past_a_decorator_to_the_block_above_it() -> None:
    # The marker sits above the whole definition, decorators included — asking
    # an author to wedge it between a decorator and its def would be absurd.
    src = (
        "# tesser-category: dto\n"
        "@staticmethod\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view\n"
    )
    assert _tb032(src) == []


def test_tb032_marker_does_not_attach_across_a_blank_line() -> None:
    # Contiguous on purpose. A marker separated from its definition attaches to
    # nothing in particular, and walking up through blanks would let it reach
    # the previous function's trailing comment instead.
    src = (
        "# tesser-category: dto\n"
        "\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    assert [f.line for f in _tb032(src)] == [3]


def test_tb032_reports_an_unknown_category_as_a_typo_not_as_a_bad_helper() -> None:
    # The two findings are different diagnoses and must not be confused: this
    # author wrote a marker, they just misspelled it. Telling them their helper
    # "does not classify" would send them to rewrite conformant code.
    src = _SPEC_DEF + (
        "# tesser-category: builder\n"
        "def _spec() -> LinkSpec:\n"
        "    return LinkSpec(slug='a')\n"
        "def test_it() -> None:\n"
        "    assert _spec()\n"
    )
    findings = _tb032(src)
    assert len(findings) == 1
    assert "unknown test-helper category 'builder'" in findings[0].message


def test_tb032_marker_must_be_a_real_comment_not_a_string_literal() -> None:
    # Same spoof resistance as TB030's marker: a string that merely CONTAINS
    # the marker text is data, not a directive.
    src = (
        "SRC = '# tesser-category: dto'\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    assert [f.line for f in _tb032(src)] == [2]


def test_tb032_honors_the_tessercheck_ignore_hatch() -> None:
    src = (
        "def _detect(x: int) -> int:  # tessercheck:ignore\n"
        "    return x\n"
        "def test_it() -> None:\n"
        "    assert _detect(1) == 1\n"
    )
    assert _tb032(src) == []


def _tb033(src: str) -> list[Finding]:
    return [f for f in check_source("t.py", src, is_test=False) if f.code == "TB033"]


def test_tb033_ignores_a_builtin_name_that_is_never_called() -> None:
    # The whole ruling: the name is not the problem. A parameter or field named
    # `id` leaves id() working everywhere a human writes code, so a name-based
    # ban (ruff A001/A002) would flag conformant code here.
    src = (
        "def load(self, id: str) -> str:\n"
        "    return self._store[id]\n"
    )
    assert _tb033(src) == []


def test_tb033_flags_a_parameter_that_is_also_called() -> None:
    src = "def f(id: str) -> str:\n    return str(id(object()))\n"
    assert [f.line for f in _tb033(src)] == [2]


def test_tb033_flags_a_local_binding_the_same_scope_calls() -> None:
    # Same bug one line away from the parameter case. Excluding locals would
    # leave `len = 0` then `len(name)` uncaught.
    src = "def widest(names: list[str]) -> int:\n    len = 0\n    return len(names)\n"
    assert [f.line for f in _tb033(src)] == [3]


def test_tb033_does_not_depend_on_the_binding_coming_first() -> None:
    # Python scopes per FUNCTION, not per statement: any assignment makes the
    # name local for the whole body, so a call placed EARLIER raises
    # UnboundLocalError rather than reaching the builtin. Verified by running
    # both orders; either way the code is broken, so order carries no signal.
    src = "def f(x: object) -> object:\n    n = id(x)\n    id = n\n    return id\n"
    assert [f.line for f in _tb033(src)] == [2]


def test_tb033_does_not_read_a_subscript_index_as_a_binding() -> None:
    # Regression: `self._by_id[str(c.id)] = rec` binds nothing, but walking the
    # assignment target descends into the index expression. This produced 4
    # false positives on the example trees. The Subscript carries the Store;
    # names inside the index are Loads.
    src = (
        "class Repo:\n"
        "    def save(self, c: object) -> None:\n"
        "        self._by_id[str(c)] = c\n"
    )
    assert _tb033(src) == []


def test_tb033_leaves_an_unshadowed_builtin_call_alone() -> None:
    src = "def size(items: list[str]) -> int:\n    return len(items)\n"
    assert _tb033(src) == []


def test_tb033_scopes_per_function_not_per_module() -> None:
    # A binding in one function must not implicate a call in its sibling.
    src = (
        "def binder() -> None:\n"
        "    id = 1\n"
        "    return None\n"
        "def caller(x: object) -> int:\n"
        "    return id(x)\n"
    )
    assert _tb033(src) == []


def test_tb033_flags_an_async_function_too() -> None:
    src = "async def f(hash: str) -> int:\n    return hash(hash)\n"
    assert [f.line for f in _tb033(src)] == [2]


def test_tb033_honors_the_ignore_hatch() -> None:
    # The documented escape for a callable binding legitimately called —
    # `def apply(filter, xs): return filter(xs)`.
    src = (
        "def apply(filter: object, xs: list[str]) -> object:\n"
        "    return filter(xs)  # tessercheck:ignore\n"
    )
    assert _tb033(src) == []


def test_tb032_comment_read_fails_closed_when_the_source_will_not_tokenize() -> None:
    # The fail-closed contract, stated in _comment_lines and otherwise unproven:
    # with no comments read, NO marker is honored, so every undeclarable
    # function reports. A marker that silently stops working — turning the
    # totality check into a no-op — is the failure worth avoiding, and the
    # opposite default (fail open) would do exactly that.
    assert _comment_lines("x = (  # tesser-category: dto\n") == {}
    assert _comment_lines("x = 1  # tesser-category: dto\n") == {
        1: "# tesser-category: dto"
    }


def test_tb032_flags_a_helper_with_no_return_annotation() -> None:
    # `node.returns is None` is the first gate in _returns_a_spec. An
    # unannotated helper cannot be shown to build a spec, so it must report
    # rather than slip through the structural arm on an absent signal.
    src = (
        "def _helper(x=1):\n"
        "    return x\n"
        "def test_it() -> None:\n"
        "    assert _helper()\n"
    )
    assert [f.line for f in _tb032(src)] == [1]


def test_tb032_resolves_a_dotted_return_annotation() -> None:
    # _annotation_names collects Attribute.attr as well as Name.id, so a helper
    # annotated `-> wire.LinkSpec` classifies exactly like `-> LinkSpec`. Without
    # the Attribute arm, every helper in a module that imports its spec by
    # module name would need a marker to say what the code already says.
    src = _SPEC_DEF + (
        "import wire\n"
        "def _spec() -> wire.LinkSpec:\n"
        "    return wire.LinkSpec(slug='a')\n"
        "def test_it() -> None:\n"
        "    assert _spec()\n"
    )
    assert _tb032(src) == []


def test_tb032_flags_a_helper_returning_a_domain_object_not_a_spec() -> None:
    # The rule's actual teeth, and the one path where registry AND local both
    # resolve the name yet the answer is still "no": the annotation names a
    # classified type that is not a SPEC. A helper returns a spec or a DTO — a
    # constructed domain object is built at the call site, in the test.
    src = (
        "class Campaign:\n"
        "    def __init__(self, name: str) -> None:\n"
        "        self._name = name\n"
        "def _campaign() -> Campaign:\n"
        "    return Campaign('a')\n"
        "def test_it() -> None:\n"
        "    assert _campaign()\n"
    )
    assert [f.line for f in _tb032(src)] == [4]


def test_tb032_marker_reaches_up_through_a_contiguous_comment_block() -> None:
    # _declared_on walks UP line by line, not just one line. A marker under a
    # note (or over one) still attaches, because a comment block above a
    # definition is one block — stopping at the first line would make the
    # marker's placement inside it load-bearing for no reason a reader could
    # guess.
    below_a_note = (
        "# tessercheck:" + "ignore is not what this says\n"
        "# tesser-category: dto\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    above_a_note = (
        "# tesser-category: dto\n"
        "# and here is why\n"
        "def _view() -> dict[str, str]:\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    assert _tb032(below_a_note) == []
    assert _tb032(above_a_note) == []


def test_tb032_falls_back_to_the_block_above_a_non_marker_trailing_comment() -> None:
    # A trailing comment that is not a category marker must not consume the
    # lookup: the def line carries `# noqa`, the marker sits above, and the
    # helper is declared. Returning early on any trailing comment would drop it.
    src = (
        "# tesser-category: dto\n"
        "def _view() -> dict[str, str]:  # noqa\n"
        "    return {}\n"
        "def test_it() -> None:\n"
        "    assert _view() == {}\n"
    )
    assert _tb032(src) == []


def test_tb032_judges_a_helper_carrying_a_decorator_that_is_not_a_fixture() -> None:
    # _is_fixture scans the WHOLE decorator list and falls through when none
    # matches. A decorated non-fixture must not be exempted by the mere presence
    # of a decorator, and the finding must point at the def, not the decorator.
    src = (
        "import functools\n"
        "@functools.cache\n"
        "def _detect(x: int) -> int:\n"
        "    return x\n"
        "def test_it() -> None:\n"
        "    assert _detect(1) == 1\n"
    )
    assert [f.line for f in _tb032(src)] == [3]


def test_tb033_suppression_read_fails_closed_when_the_source_will_not_tokenize() -> None:
    # Fail closed in the OPPOSITE direction from _comment_lines, and for the
    # same reason: an unreadable source yields no suppressions, so findings are
    # reported rather than silently swallowed by a hatch nobody can see.
    assert _suppressed_lines("x = (  # tessercheck:ignore\n") == frozenset()
    assert _suppressed_lines("x = 1  # tessercheck:ignore\n") == frozenset({1})


@pytest.mark.parametrize(
    ("label", "src", "line"),
    [
        ("vararg", "def f(*len: int) -> int:\n    return len(len)\n", 2),
        ("kwarg", "def f(**dict: int) -> object:\n    return dict(x=1)\n", 2),
        (
            "augassign",
            "def f(xs: list[str]) -> int:\n    sum = 0\n    sum += 1\n    return sum(xs)\n",
            4,
        ),
        (
            "for",
            "def f(xs: list[str]) -> object:\n    for id in xs:\n        pass\n    return id(xs)\n",
            4,
        ),
        (
            "async for",
            "async def f(xs: object) -> object:\n    async for id in xs:\n        pass\n"
            "    return id(xs)\n",
            4,
        ),
        (
            "walrus",
            "def f(xs: list[str]) -> int:\n    if (len := 0):\n        pass\n    return len(xs)\n",
            4,
        ),
        (
            "with",
            "def f(xs: list[str]) -> object:\n    with open('p') as vars:\n        pass\n"
            "    return vars(xs)\n",
            4,
        ),
        (
            "annassign",
            "def f(xs: list[str]) -> int:\n    len: int = 0\n    return len(xs)\n",
            3,
        ),
        (
            "tuple unpack",
            "def f(xs: list[str]) -> int:\n    len, other = 0, 1\n    return len(xs)\n",
            3,
        ),
    ],
)
def test_tb033_sees_every_binding_form(label: str, src: str, line: int) -> None:
    # Python binds a name in a dozen syntactic shapes and the bug is identical
    # in all of them — `for id in xs` breaks a later id() call exactly as
    # `id = 1` does. Enumerating them here is what stops the check from
    # quietly covering only the Assign case its fixture happens to use.
    assert [f.line for f in _tb033(src)] == [line], label


def test_tb033_judges_a_lambda_in_its_own_scope_not_the_enclosing_one() -> None:
    # Two claims. The lambda's parameter binds in ITS scope, so the ENCLOSING
    # function is innocent — nothing is reported against `f`. But the lambda is
    # itself a scope, so `id(1)` inside it IS reported, at the lambda's line.
    # (This started life as a test locking the blind spot; adversarial review
    # showed the blind spot was a real false negative, so it now locks the fix.)
    src = "def f() -> object:\n    g = lambda id: id(1)\n    return g\n"
    assert [x.line for x in _tb033(src)] == [2]


def test_tb033_does_not_read_a_nested_class_body_as_the_enclosing_scope() -> None:
    # _own_scope prunes ClassDef for the same reason: `id = 1` in a class body
    # is a class attribute, not a local of the enclosing function, so the
    # function's own id() call still reaches the builtin.
    src = (
        "def f(x: object) -> object:\n"
        "    class C:\n"
        "        id = 1\n"
        "    return id(x)\n"
    )
    assert _tb033(src) == []


def test_tb033_analyzes_module_scope_too() -> None:
    # `scopes` seeds with the module itself. A module-level `id = 1` followed by
    # a module-level id() call is the same bug with no function in sight, and a
    # function-only walk would miss it entirely.
    assert [f.line for f in _tb033("id = 1\nprint(id(2))\n")] == [2]
    assert _tb033("x = 1\nprint(len('a'))\n") == []


def test_tb033_leaves_a_nested_function_reading_a_closure_alone() -> None:
    # The documented known hole: `inner` calling a name its ENCLOSING function
    # bound sees the closure variable, not the builtin. Each scope is analyzed
    # on its own, so this is not reported. Pinned so the hole is a decision
    # rather than a surprise.
    src = (
        "def outer(x: object) -> object:\n"
        "    id = 1\n"
        "    def inner(y: object) -> object:\n"
        "        return id(y)\n"
        "    return inner\n"
    )
    assert _tb033(src) == []


# Adversarial-review regressions (Codex, 2026-07-26). Each of these reproduced
# against the shipped checker before the fix; they are the expensive class for an
# analyzer that runs in other people's CI.

def test_tb032_accepts_a_forward_reference_annotation() -> None:
    # `-> "LinkSpec"` carries no ast.Name at all, so a plain walk saw nothing and
    # reported a conformant spec helper. Quoted annotations are idiomatic, and a
    # false positive here reddens a consumer's build.
    src = _SPEC_DEF + (
        'def _spec() -> "LinkSpec":\n'
        "    return LinkSpec(slug='a')\n"
        "def test_it() -> None:\n"
        "    assert _spec()\n"
    )
    assert _tb032(src) == []


def test_tb032_accepts_a_forward_reference_inside_a_collection() -> None:
    src = _SPEC_DEF + (
        'def _specs() -> list["LinkSpec"]:\n'
        "    return []\n"
        "def test_it() -> None:\n"
        "    assert _specs() == []\n"
    )
    assert _tb032(src) == []


def test_tb032_does_not_credit_a_spec_named_inside_type_or_callable() -> None:
    # `type[LinkSpec]` returns the CLASS and `Callable[[], LinkSpec]` returns a
    # factory. Neither is a built spec, so neither may bless the helper.
    for annotation in ("type[LinkSpec]", "Callable[[], LinkSpec]"):
        src = _SPEC_DEF + (
            "from typing import Callable\n"
            f"def _f() -> {annotation}:\n"
            "    return LinkSpec\n"
            "def test_it() -> None:\n"
            "    assert _f()\n"
        )
        assert _tb032(src), f"{annotation} was wrongly accepted as spec-returning"


def test_tb033_ignores_a_call_in_a_parameter_default() -> None:
    # A default is evaluated in the ENCLOSING scope at definition time, where the
    # parameter does not exist yet — so this calls the builtin and is correct.
    assert _tb033('def f(len=len("ab")) -> int:\n    return len\n') == []


def test_tb033_judges_a_lambda_scope() -> None:
    assert [f.line for f in _tb033("g = lambda len: len(1)\n")] == [1]


def test_tb033_judges_a_class_body() -> None:
    # A class body executes at IMPORT time, so this breaks the module for every
    # importer — the worst case to be blind to.
    src = "class C:\n    len = 0\n    x = len('a')\n"
    assert [f.line for f in _tb033(src)] == [3]


def test_tb033_counts_an_except_alias_as_a_binding() -> None:
    # `except E as name` binds name for the handler body, but the alias is a
    # plain str on the handler, not a Name node, so the target walk never saw it.
    src = (
        "def f(xs: list) -> None:\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as len:\n"
        "        print(len(xs))\n"
    )
    assert [f.line for f in _tb033(src)] == [5]


def test_tb033_declines_to_judge_a_global_or_nonlocal_rebind() -> None:
    # `global len` means the binding is not local, so which target the call
    # reaches depends on execution order — undecidable from one AST pass.
    # Reporting it would be a false positive; silence is the honest answer.
    src = (
        "def f(xs: list) -> int:\n"
        "    global len\n"
        "    n = len(xs)\n"
        "    len = 0\n"
        "    return n\n"
    )
    assert _tb033(src) == []


def test_tb032_depth_cap_bounds_quote_nesting_not_plain_nesting() -> None:
    # The recursion guard in _annotation_names bounds RE-ENTRY through parsed
    # string annotations only. An earlier cut capped ordinary AST descent too,
    # and adversarial review proved that an escape hatch: five levels of
    # generic nesting hid a primitive from the "any name anywhere" ban. So:
    # plain nesting resolves at ANY depth (the deleted ast.walk copies had no
    # cap, and the shared walk must not be weaker), while a string quoted
    # inside a string past eight parses is nobody's type and degrades to a
    # finding rather than recursing without bound.
    deep_plain = "list[" * 12 + "LinkSpec" + "]" * 12
    realistic_quoted = repr(repr("list[LinkSpec]"))
    absurd_quoted = "list[LinkSpec]"
    for _ in range(10):
        absurd_quoted = repr(absurd_quoted)
    body = (
        "def _specs() -> {ann}:\n"
        "    return []\n"
        "def test_it() -> None:\n"
        "    assert _specs() == []\n"
    )
    assert _tb032(_SPEC_DEF + body.format(ann=deep_plain)) == []
    assert _tb032(_SPEC_DEF + body.format(ann=realistic_quoted)) == []
    assert [f.line for f in _tb032(_SPEC_DEF + body.format(ann=absurd_quoted))] == [5]


def test_tb032_survives_a_forward_reference_that_will_not_parse() -> None:
    # A string annotation is arbitrary text, so ast.parse on it can raise where
    # the module's own parse succeeded. The analyzer must not crash on source
    # its host tool accepted — it degrades to "no names resolved", which reports
    # the helper. Fail closed, same posture as the tokenize handlers.
    src = _SPEC_DEF + (
        'def _spec() -> "LinkSpec[":\n'
        "    return LinkSpec(slug='a')\n"
        "def test_it() -> None:\n"
        "    assert _spec()\n"
    )
    assert [f.line for f in _tb032(src)] == [5]


def test_tb033_scope_roots_excludes_what_the_enclosing_scope_evaluates() -> None:
    # _scope_roots is the fix for the parameter-default false positive, and its
    # contract is worth pinning directly: for a def, ONLY the body executes in
    # the new scope — a default, a decorator, and an annotation are all
    # evaluated at definition time in the enclosing one. The final fallback is
    # unreachable through check_shadowing (every scope root is a Module,
    # Function, Lambda or ClassDef today) and exists so a non-scope node
    # degrades to its children rather than silently yielding nothing.
    fn = ast.parse("@deco\ndef f(len=len('ab')) -> len:\n    return 1\n").body[0]
    assert [type(n).__name__ for n in _scope_roots(fn)] == ["Return"]
    lam = ast.parse("lambda id: id(1)", mode="eval").body
    assert [type(n).__name__ for n in _scope_roots(lam)] == ["Call"]
    branch = ast.parse("if x:\n    y = 1\n").body[0]
    assert [type(n).__name__ for n in _scope_roots(branch)] == ["Name", "Assign"]


def test_tb032_ignores_a_production_class_with_a_test_prefixed_method() -> None:
    # The P1 from the structured review, and the flip side of walking past
    # tree.body: a production `Client.test_connection()` must not make the whole
    # module a test module and drag `build_url` into TB032's scope. Detection
    # mirrors pytest's own collection — module-level test_*, or test_* on a
    # class named Test*.
    src = (
        "def build_url(host: str, port: int) -> str:\n"
        '    return f"{host}:{port}"\n'
        "class Client:\n"
        "    def test_connection(self) -> bool:\n"
        "        return True\n"
    )
    assert _tb032(src) == []


def test_tb032_still_judges_a_class_named_test_something() -> None:
    # The other half of the same predicate: narrowing to pytest's rules must not
    # undo the class-based-tests fix.
    src = (
        "def _detect(x: int) -> int:\n"
        "    return x\n"
        "class TestThing:\n"
        "    def test_it(self) -> None:\n"
        "        assert _detect(1) == 1\n"
    )
    assert [f.line for f in _tb032(src)] == [1]


def test_tb032_reads_a_trailing_marker_on_a_decorated_helpers_def_line() -> None:
    # `_anchor_line` is the DECORATOR line for a decorated function, so the
    # documented "trailing its def" form was never read and produced a false
    # positive on a correctly-annotated helper.
    src = (
        "from contextlib import contextmanager\n"
        "@contextmanager\n"
        "def _payload():  # tesser-category: dto\n"
        "    yield {}\n"
        "def test_it() -> None:\n"
        "    assert _payload\n"
    )
    assert _tb032(src) == []


def test_tb020_flags_prose_riding_a_category_prefix() -> None:
    # The exemption is on the marker's SHAPE, not a bare prefix. Prose after the
    # prefix is not a marker, so it stays a banned comment instead of using a
    # directive as cover.
    assert _tb020("x = 1  # tesser-category: spec because it builds one\n")


def test_tb020_still_exempts_a_typod_category_name() -> None:
    # ...while a misspelled name DOES parse as a marker and stays exempt here,
    # so the author gets one finding from TB032 with the right diagnosis rather
    # than two with the wrong one leading.
    assert _tb020("x = 1  # tesser-category: spce\n") == []


@pytest.mark.parametrize(
    "declaration",
    [
        "import unittest\nclass CampaignCase(unittest.TestCase):",
        "from unittest import TestCase\nclass CampaignCase(TestCase):",
    ],
)
def test_tb032_judges_a_unittest_testcase_whatever_it_is_named(declaration: str) -> None:
    # pytest collects a TestCase subclass regardless of its name, so narrowing
    # detection to `Test*` classes silently skipped every helper in a module
    # written in the most standard test style there is. A false negative, and
    # the kind that looks like a clean report.
    src = "def _detect(x: int) -> int:\n    return x\n" + declaration + (
        "\n    def test_it(self) -> None:\n        assert _detect(1) == 1\n"
    )
    assert [f.line for f in _tb032(src)] == [1]


def test_tb032_needs_a_collectible_test_not_merely_a_collectible_class() -> None:
    # The class arm requires BOTH halves: a class pytest would collect AND a
    # test_* method on it. A Test*-named class holding only helpers yields no
    # tests, so the module is not a test module — the same known hole as a
    # helper-only file, reached by a different route. Treating the class name
    # alone as proof would judge a module pytest collects nothing from.
    src = (
        "def _detect(x: int) -> int:\n"
        "    return x\n"
        "class TestHelpers:\n"
        "    def helper(self) -> int:\n"
        "        return 1\n"
    )
    assert _tb032(src) == []


def test_tb032_survives_an_annotation_that_defeats_the_parser() -> None:
    # A fix-induced crash, caught by adversarial review before it shipped. The
    # forward-reference repair parses the CONTENT of a string annotation — the
    # one place this checker parses text the outer file never had to parse, and
    # therefore the one place a legal file can defeat the parser. A long flat
    # expression exhausts CPython's parser recursion, and RecursionError is not
    # a SyntaxError, so catching only that aborted the ENTIRE run: every other
    # file in the tree went unchecked because of one file.
    #
    # Failing closed means crediting no name, so the helper reports as
    # unclassified rather than being waved through.
    bomb = "a+" * 40000 + "b"
    src = (
        f'def _spec() -> "{bomb}":\n'
        "    return 1\n"
        "def test_it() -> None:\n"
        "    assert _spec()\n"
    )
    findings = _tb032(src)
    assert [f.line for f in findings] == [1]


# --- quoted annotations are not an escape hatch, anywhere ---------------------
#
# The annotation-name walk existed as three diverged copies, and only the
# newest (TB032's) resolved string forward references. Every check keyed on the
# classifier therefore false-positived on conformant quoted-annotation code
# (TB015 fired on every leaf VO in all four example trees under quoting), while
# the checks reading annotations directly false-negatived (a quote hid a
# primitive from TB010 and a held root from TB012). One shared walk in astutil
# now serves every reader; these lock each formerly-divergent behavior.


def test_classifier_reads_quoted_annotations_identically() -> None:
    from tessercheck.classify import classify_sources

    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class LinkSpec:\n"
        "    slug: str\n"
        "class ShortLink:\n"
        "    def __init__(self, spec: {q}LinkSpec{q}) -> None:\n"
        "        self._slug = spec.slug\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, ShortLink) and other._slug == self._slug\n"
        "class Campaign:\n"
        "    def __init__(self) -> None:\n"
        "        self._links: {q}tuple[ShortLink, ...]{q} = ()\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return other is self\n"
        "    @property\n"
        "    def links(self) -> {q}tuple[ShortLink, ...]{q}:\n"
        "        return self._links\n"
    )
    plain = classify_sources({"m.py": src.replace("{q}", "")})
    quoted = classify_sources({"m.py": src.replace("{q}", "'")})
    for name in plain:
        assert quoted[name].stereotype is plain[name].stereotype, name
        assert quoted[name].embeds_entity == plain[name].embeds_entity, name
        assert quoted[name].is_member == plain[name].is_member, name
        assert quoted[name].field_type_names == plain[name].field_type_names, name
    assert plain["Campaign"].is_aggregate_root


def test_tb015_quoted_leaf_annotation_is_still_a_leaf() -> None:
    # The false positive that made the divergence a live bug: a quoted backing
    # field read as "not a scalar", the leaf became structured, and its one
    # legitimate exit was flagged as an illegal dunder — on every leaf VO in
    # all four example trees.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: 'str'\n"
        "    def __str__(self) -> 'str':\n"
        "        return self._value\n"
    )
    assert "TB015" not in _codes(src)


def test_tb010_quoted_primitive_return_is_not_an_escape_hatch() -> None:
    # The mirror-image false negative: the direct annotation readers had NO
    # forward-reference resolution, so quoting a primitive hid it from the
    # accessor ban.
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slot:\n"
        "    _key: str\n"
        "    def key(self) -> 'str':\n"
        "        return self._key\n"
    )
    assert "TB010" in _codes(src)


def test_tb012_quoted_held_root_is_not_an_escape_hatch() -> None:
    base = (
        "class Shelf:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Shelf) and other._id == self._id\n"
        "class Warehouse:\n"
        "    def __init__(self, id: str, shelves: list[Shelf]) -> None:\n"
        "        self._id = id\n"
        "        self._shelves = list(shelves)\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
        "class Order:\n"
        "    def __init__(self, id: str, warehouse: {ann}) -> None:\n"
        "        self._id = id\n"
        "        self._warehouse = warehouse\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
    )
    plain = {f.code for f in check_source("t.py", base.replace("{ann}", "Warehouse"), is_test=False)}
    quoted_findings = check_source("t.py", base.replace("{ann}", "'Warehouse'"), is_test=False)
    quoted = {f.code for f in quoted_findings}
    assert "TB012" in plain
    assert "TB012" in quoted
    held = [f for f in quoted_findings if f.code == "TB012"]
    assert held[0].line == 12


def test_classifier_survives_an_annotation_that_defeats_the_parser() -> None:
    # Same bomb as TB032's regression above, aimed at the classifier and the
    # typed checks now that they parse string annotations too: one pathological
    # field annotation must not abort the file, and failing closed means the
    # quoted name credits nothing.
    bomb = "a+" * 40000 + "b"
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        f"    _value: '{bomb}'\n"
        "    def __str__(self) -> str:\n"
        "        return self._value\n"
        "class Held:\n"
        f"    def __init__(self, x: '{bomb}') -> None:\n"
        "        self._x = x\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
    )
    check_source("t.py", src, is_test=False)


def test_literal_values_are_not_forward_references() -> None:
    # Adversarial review of the shared walk's first cut: Literal["Warehouse"]
    # is a discriminator holding a STRING, not the type it happens to spell.
    # Reading it as a forward reference made the classifier see an embedded
    # root (TB014 flipped the entity rule to the aggregate-root rule) and
    # TB012 report a held root that is not held.
    src = (
        "from typing import Literal\n"
        "class Shelf:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Shelf) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
        "class Warehouse:\n"
        "    def __init__(self, id: str, shelves: list[Shelf]) -> None:\n"
        "        self._id = id\n"
        "        self._shelves = list(shelves)\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
        "    __hash__ = None  # type: ignore[assignment]\n"
        "class AuditEntry:\n"
        "    def __init__(self, id: str, subject_kind: Literal['Warehouse']) -> None:\n"
        "        self._id = id\n"
        "        self._subject_kind = subject_kind\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, AuditEntry) and other._id == self._id\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(self._id)\n"
    )
    assert _codes(src) == set()


def test_literal_of_primitive_spellings_is_not_a_primitive() -> None:
    # Literal["str", "int"] holds the words, not the types — the accessor ban
    # must not key on a literal's CONTENT (Literal["percent"] was clean while
    # the identical shape spelling a type name fired).
    src = (
        "from dataclasses import dataclass\n"
        "from typing import Literal\n"
        "@dataclass(frozen=True)\n"
        "class Slug:\n"
        "    _value: str\n"
        "    def kind(self) -> Literal['str', 'int', 'bool']:\n"
        "        return 'str'\n"
        "    def __str__(self) -> str:\n"
        "        return self._value\n"
    )
    assert "TB010" not in _codes(src)


def test_annotated_metadata_is_not_a_forward_reference() -> None:
    # Only Annotated's FIRST argument is the type; the rest is metadata, and a
    # docstring-ish "Warehouse" there must not read as holding the root. The
    # first argument itself still resolves — quoted or not.
    src = (
        "from typing import Annotated\n"
        "class Shelf:\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "    def __eq__(self, other: object) -> bool:\n"
        "        return isinstance(other, Shelf) and other._id == self._id\n"
        "class Warehouse:\n"
        "    def __init__(self, id: str, shelves: list[Shelf]) -> None:\n"
        "        self._id = id\n"
        "        self._shelves = list(shelves)\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
        "class Order:\n"
        "    def __init__(self, id: str, note: Annotated[str, 'Warehouse']) -> None:\n"
        "        self._id = id\n"
        "        self._note = note\n"
        "    __eq__ = None  # type: ignore[assignment]\n"
    )
    assert "TB012" not in _codes(src)
    held = src.replace(
        "note: Annotated[str, 'Warehouse']", "w: Annotated['Warehouse', 'doc']"
    )
    assert "TB012" in _codes(held)


def test_deep_generic_nesting_is_not_an_escape_hatch_from_the_primitive_ban() -> None:
    # The P2 from the same review: capping plain AST descent at 8 silently
    # bounded "any name anywhere" at five levels of generic nesting, so a
    # deep-enough dict hid its primitive from TB010.
    deep = "dict[str, " * 6 + "int" + "]" * 6
    src = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Ledger:\n"
        "    _rows: tuple\n"
        f"    def rows(self) -> {deep}:\n"
        "        return self._rows\n"
    )
    assert "TB010" in _codes(src)


def test_tb017_partially_garbage_annotation_still_consults_the_body() -> None:
    # tuple["int", "not (("] credits `tuple` and `int` while silently dropping
    # the garbage part — "credits some name" alone is not trust. The old copy
    # got this via its raw-text fallback; the shared walk gets it via an
    # explicit any-string-unparseable signal.
    src = _LEAF + (
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> tuple['int', 'not valid syntax (']:\n"
        "        return cls(raw)\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_a_factory_returning_the_class_object_is_not_a_door() -> None:
    # `-> type[Slug]` returns the CLASS, not a constructed Slug. Crediting the
    # name inside called every kind_of-style classmethod a second construction
    # door; with returned_only the annotation credits nothing and the
    # non-constructing body settles it.
    for ann in ("type[Slug]", "type['Slug']"):
        src = _LEAF + (
            "    @classmethod\n"
            f"    def kind_of(cls) -> {ann}:\n"
            "        return cls\n"
        )
        assert "TB017" not in _codes(src), ann


def test_tb017_garbage_nested_one_quote_deep_still_consults_the_body() -> None:
    # The trust signal shares the walk's traversal, so it sees through a quote:
    # "tuple[int, 'not valid (']" hides its garbage one string level down, and
    # a signal computed by a separate flat ast.walk read it as trustworthy —
    # quoting must not change the answer, in either direction.
    src = _LEAF + (
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> \"tuple[int, 'not valid (']\":\n"
        "        return cls(raw)\n"
    )
    assert "TB017" in _codes(src)


def test_tb017_multiword_literal_values_are_not_garbage() -> None:
    # The inverse: Literal["percent off"] holds a VALUE with a space in it. The
    # walk skips Literal values as non-types, so the trust signal must not
    # parse them either — reading one as an unparseable forward reference sent
    # a factory returning a multi-word Literal to body inspection and a TB017
    # false positive.
    src = _LEAF + (
        "    @classmethod\n"
        "    def describe(cls, raw: str) -> Literal['percent off', 'flat amount']:\n"
        "        made = cls(raw)\n"
        "        return 'percent off' if made else 'flat amount'\n"
    )
    src = "from typing import Literal\n" + src
    assert "TB017" not in _codes(src)


def test_tb017_garbage_inside_an_excluded_slot_does_not_discredit_the_annotation() -> None:
    # The trust signal takes the same returned_only the name set beside it was
    # computed with: `tuple[int, Callable[[], "junk ("]]` cleanly names types
    # in returned position, and the garbage sits inside a Callable slot that is
    # not the returned value — so the annotation is taken at its word and the
    # constructing body is never consulted.
    src = _LEAF + (
        "    @classmethod\n"
        "    def pair(cls, raw: str) -> tuple[int, Callable[[], 'junk (']]:\n"
        "        made = cls(raw)\n"
        "        return (1, lambda: made)\n"
    )
    src = "from typing import Callable\n" + src
    assert "TB017" not in _codes(src)
