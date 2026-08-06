import ast

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
