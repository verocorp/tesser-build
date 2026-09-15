from __future__ import annotations

import calls.client as client


class TestCallNotFound:

    def test_a_call_that_was_not_found_carries_its_message(self) -> None:
        call_not_found = client.CallNotFound("no call 'c1'")

        assert call_not_found.message == "no call 'c1'"

    def test_a_call_that_was_not_found_reads_as_its_message(self) -> None:
        call_not_found = client.CallNotFound("no call 'c1'")

        assert str(call_not_found) == "no call 'c1'"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }

        assert {error.__name__ for error in client.ERRORS} == raised
