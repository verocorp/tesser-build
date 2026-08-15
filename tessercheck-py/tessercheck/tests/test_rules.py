import ast
from pathlib import Path

import pytest

import tessercheck.adapters.repositories as repositories
import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.domain.rulebook as rulebook


def test_rules_md_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    read = repositories.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(root=str(root))
    )
    rendered = rulebook.render(
        read.checks_text,
        tuple((module.name, module.text) for module in read.test_modules),
        read.contracts_text,
    )
    output = root / "RULES.md"
    assert output.exists(), "RULES.md missing; generate with: python3 -m srv.cli.rules"
    assert output.read_text() == rendered, (
        "RULES.md is stale; regenerate with: python3 -m srv.cli.rules"
    )


def test_every_rule_has_a_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    read = repositories.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(root=str(root))
    )
    assertions = rulebook.test_assertions(
        tuple((module.name, module.text) for module in read.test_modules)
    )
    uncovered = [
        str(row.clause())
        for row in rulebook.rule_rows(ast.parse(read.checks_text))
        if not rulebook.covering_tests(str(row.clause()), assertions)
    ]
    assert uncovered == [], f"rules with no fixture (NONE rows): {uncovered}"


def test_a_violation_call_takes_four_positional_args() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation('only-message; a clause')\n"
    )
    with pytest.raises(RuntimeError, match="exactly the four"):
        rulebook.rule_rows(tree)


def test_a_violation_code_must_be_literal_or_bound() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation(p, 1, computed, 'head; a clause')\n"
    )
    with pytest.raises(RuntimeError, match="neither a literal"):
        rulebook.rule_rows(tree)


def test_one_clause_carries_one_code() -> None:
    tree = ast.parse(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Codebase:\n"
        "    def _module_violations(self) -> None:\n"
        "        Violation('p', 1, 'TB040', 'a head; one shared clause')\n"
        "        Violation('p', 1, 'TB041', 'b head; one shared clause')\n"
    )
    with pytest.raises(RuntimeError, match="one clause has one code"):
        rulebook.rule_rows(tree)
