import ast
import pathlib
import re

import tessercheck.adapters.repositories.rulebook_sources as rulebook_repository
import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.domain.rulebook as rulebook


def test_rules_md_is_current() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(root))
    )
    rendered = str(
        rulebook.Rulebook(
            rulebook.RulebookSpec(
                read.checks_text,
                tuple((module.name, module.text) for module in read.test_modules),
                read.contracts_text,
            )
        )
    )
    output = root / "RULES.md"
    assert output.exists(), "RULES.md missing; generate with: python3 -m srv.cli.rules"
    assert output.read_text() == rendered, (
        "RULES.md is stale; regenerate with: python3 -m srv.cli.rules"
    )


def test_every_applies_to_row_is_reached_by_a_violation() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(root))
    )
    rulebook.Rulebook(
        rulebook.RulebookSpec(
            read.checks_text,
            tuple((module.name, module.text) for module in read.test_modules),
            read.contracts_text,
            True,
        )
    )


def test_every_rule_has_a_fixture() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(root))
    )
    rendered = str(
        rulebook.Rulebook(
            rulebook.RulebookSpec(
                read.checks_text,
                tuple((module.name, module.text) for module in read.test_modules),
                read.contracts_text,
            )
        )
    )
    uncovered = [
        line.split(" | ")[1]
        for line in rendered.splitlines()
        if line.startswith("| TB") and line.endswith("| NONE |")
    ]
    assert uncovered == [], f"rules with no fixture (NONE rows): {uncovered}"


def test_every_violation_site_yields_a_rulebook_row() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
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
    rendered = str(
        rulebook.Rulebook(
            rulebook.RulebookSpec(
                read.checks_text,
                tuple((module.name, module.text) for module in read.test_modules),
                read.contracts_text,
            )
        )
    )
    rows = [line for line in rendered.splitlines() if line.startswith("| TB")]
    rendered_lines = {
        int(number)
        for row in rows
        for number in re.findall(r"domain/checks\.py:([0-9,]+)", row)
        for number in number.split(",")
    }
    assert sites, "no Violation construction site was found; the scan itself is broken"
    site_lines = {site.lineno for site in sites}
    dropped = sorted(site_lines - rendered_lines)
    assert dropped == [], (
        f"Violation sites at checks.py lines {dropped} yield no rulebook row; "
        "a construction shape the generator cannot read drops rules silently, "
        "and test_every_rule_has_a_fixture then passes vacuously"
    )
    phantom = sorted(rendered_lines - site_lines)
    assert phantom == [], (
        f"rulebook rows cite checks.py lines {phantom} with no Violation site; "
        "a row that names no construction site describes a rule that does not exist"
    )
