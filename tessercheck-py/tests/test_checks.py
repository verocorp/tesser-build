"""Per-check good/bad behavior, the test-scoping exemption, and suppression."""

from pathlib import Path

import pytest

from tessercheck.checks import check_source
from tessercheck.finding import CHECKS
from tessercheck.run import run_source

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
