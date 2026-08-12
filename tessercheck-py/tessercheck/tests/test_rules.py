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


def test_a_violation_call_takes_four_positional_args() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation('only-message; a clause')\n"
    )
    with pytest.raises(RuntimeError, match="exactly the four"):
        rules.rule_rows(tree)


def test_a_violation_code_must_be_literal_or_bound() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation(p, 1, computed, 'head; a clause')\n"
    )
    with pytest.raises(RuntimeError, match="neither a literal"):
        rules.rule_rows(tree)


def test_one_clause_carries_one_code() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation('p', 1, 'TB040', 'a head; one shared clause')\n"
        "        Violation('p', 1, 'TB041', 'b head; one shared clause')\n"
    )
    with pytest.raises(RuntimeError, match="one clause has one code"):
        rules.rule_rows(tree)
