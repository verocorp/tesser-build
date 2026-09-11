from __future__ import annotations

import beta.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("empty_key", "a key is never empty")
        assert rejected.code == "empty_key"
        assert rejected.message == "a key is never empty"
        assert str(rejected) == "a key is never empty"


class TestUnavailable:

    def test_an_unavailable_store_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the key store is unavailable")
        assert unavailable.message == "the key store is unavailable"
        assert str(unavailable) == "the key store is unavailable"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
