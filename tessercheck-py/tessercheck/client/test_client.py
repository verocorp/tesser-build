from __future__ import annotations

import tessercheck.client as client


class TestRulebookNotRendered:

    def test_a_rulebook_that_was_not_rendered_carries_its_code_and_message(self) -> None:
        rulebook_not_rendered = client.RulebookNotRendered(
            "rulebook_unreadable", "TS_NAME_BY_BLOCK not found in checks.py"
        )
        assert rulebook_not_rendered.code == "rulebook_unreadable"
        assert rulebook_not_rendered.message == "TS_NAME_BY_BLOCK not found in checks.py"
        assert str(rulebook_not_rendered) == "TS_NAME_BY_BLOCK not found in checks.py"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {name for name, value in vars(client).items() if isinstance(value, type) and issubclass(value, Exception)}
        assert {error.__name__ for error in client.ERRORS} == raised


class TestTreeNotInspected:

    def test_an_inspection_error_carries_its_domain_code_and_message(self) -> None:
        tree_not_inspected = client.TreeNotInspected("inspection_syntax", "broken.py: invalid syntax")
        assert tree_not_inspected.code == "inspection_syntax"
        assert tree_not_inspected.message == "broken.py: invalid syntax"
        assert str(tree_not_inspected) == "broken.py: invalid syntax"
