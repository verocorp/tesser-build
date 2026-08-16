import ast
from pathlib import Path

import tessercheck.adapters.repositories.rulebook_sources as rulebook_repository
import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.domain.rulebook as rulebook


def test_rules_md_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
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
    read = rulebook_repository.FilesystemRulebookSources().read(
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
