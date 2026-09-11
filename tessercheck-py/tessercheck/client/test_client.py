from __future__ import annotations

import tessercheck.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("unreadable", "TS_NAME_BY_BLOCK not found in checks.py")
        assert rejected.code == "unreadable"
        assert rejected.message == "TS_NAME_BY_BLOCK not found in checks.py"
        assert str(rejected) == "TS_NAME_BY_BLOCK not found in checks.py"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {name for name, value in vars(client).items() if isinstance(value, type) and issubclass(value, Exception)}
        assert {error.__name__ for error in client.ERRORS} == raised
