import ast

import pytest

import rules


def test_rules_md_is_current() -> None:
    assert rules.OUTPUT.exists(), "RULES.md missing; generate with: python3 rules.py"
    assert rules.OUTPUT.read_text() == rules.render(), (
        "RULES.md is stale; regenerate with: python3 rules.py"
    )


def test_every_rule_has_a_fixture() -> None:
    tree = ast.parse(rules.DOMAIN.read_text())
    assertions = rules.test_assertions()
    uncovered = [
        row.clause
        for row in rules.rule_rows(tree)
        if not rules.covering_tests(row.clause, assertions)
    ]
    assert uncovered == [], f"rules with no fixture (NONE rows): {uncovered}"


def test_tooling_modules_wrong_shape_is_its_own_error() -> None:
    tree = ast.parse(
        "from typing import Final\nTOOLING_MODULES: Final[frozenset[str]] = frozenset([1])\n"
    )
    with pytest.raises(RuntimeError, match="unexpected shape"):
        rules.tooling_modules(tree)


def test_an_underived_exemption_guard_fails_the_render() -> None:
    tree = ast.parse(
        "class Codebase:\n"
        "    def _module_violations(self, basename: str) -> tuple[str, ...]:\n"
        "        if basename == 'stray':\n"
        "            return ()\n"
        "        return ()\n"
    )
    with pytest.raises(RuntimeError, match="do not match"):
        rules.ungoverned_bullets(tree)
