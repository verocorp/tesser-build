import rules


def test_rules_md_is_current() -> None:
    assert rules.OUTPUT.exists(), "RULES.md missing; generate with: python3 rules.py"
    assert rules.OUTPUT.read_text() == rules.render(), (
        "RULES.md is stale; regenerate with: python3 rules.py"
    )
