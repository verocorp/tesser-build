from __future__ import annotations

import alpha.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("empty_name", "a name is never empty")
        assert rejected.code == "empty_name"
        assert rejected.message == "a name is never empty"
        assert str(rejected) == "a name is never empty"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {name for name, value in vars(client).items() if isinstance(value, type) and issubclass(value, Exception)}
        assert {error.__name__ for error in client.ERRORS} == raised
