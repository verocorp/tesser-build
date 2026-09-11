from __future__ import annotations

import linkpolicy.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("invalid_target_url", "target url 'nope' must be http(s)")
        assert rejected.code == "invalid_target_url"
        assert rejected.message == "target url 'nope' must be http(s)"
        assert str(rejected) == "target url 'nope' must be http(s)"


class TestUnavailable:

    def test_an_unavailable_store_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the verdict store is unavailable")
        assert unavailable.message == "the verdict store is unavailable"
        assert str(unavailable) == "the verdict store is unavailable"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
