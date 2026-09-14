from __future__ import annotations

import linkpolicy.client as client


class TestTargetRejected:

    def test_a_rejected_target_carries_its_code_and_message(self) -> None:
        target_rejected = client.TargetRejected(
            "invalid_target_url", "target url 'nope' must be http(s)"
        )
        assert target_rejected.code == "invalid_target_url"
        assert target_rejected.message == "target url 'nope' must be http(s)"
        assert str(target_rejected) == "target url 'nope' must be http(s)"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
