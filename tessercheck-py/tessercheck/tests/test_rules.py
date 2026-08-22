import ast
from pathlib import Path

import tessercheck.adapters.repositories.rulebook_sources as rulebook_repository
import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.domain.rulebook as rulebook


def test_rules_md_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(root))
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
        rulebook_sources.ReadRulebookRequest(tree=str(root))
    )
    rendered = rulebook.render(
        read.checks_text,
        tuple((module.name, module.text) for module in read.test_modules),
        read.contracts_text,
    )
    uncovered = [
        line.split(" | ")[1]
        for line in rendered.splitlines()
        if line.startswith("| TB") and line.endswith("| NONE |")
    ]
    assert uncovered == [], f"rules with no fixture (NONE rows): {uncovered}"


def test_every_violation_site_yields_a_rulebook_row() -> None:
    root = Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(root))
    )
    sites = [
        node
        for node in ast.walk(ast.parse(read.checks_text))
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "Violation")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "Violation")
        )
    ]
    rendered = rulebook.render(
        read.checks_text,
        tuple((module.name, module.text) for module in read.test_modules),
        read.contracts_text,
    )
    rows = [line for line in rendered.splitlines() if line.startswith("| TB")]
    assert sites, "no Violation construction site was found; the scan itself is broken"
    assert len(rows) == len(sites), (
        f"{len(sites)} Violation sites produced {len(rows)} rulebook rows; "
        "a construction shape the generator cannot read drops rules silently, "
        "and test_every_rule_has_a_fixture then passes vacuously"
    )
