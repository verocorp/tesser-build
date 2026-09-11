from __future__ import annotations

import reports.client as client


class TestUnavailable:

    def test_an_unavailable_source_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the link source is unavailable")
        assert unavailable.message == "the link source is unavailable"
        assert str(unavailable) == "the link source is unavailable"


class TestUnreadable:

    def test_an_unreadable_record_carries_its_message(self) -> None:
        unreadable = client.Unreadable("a record the report cannot read")
        assert unreadable.message == "a record the report cannot read"
        assert str(unreadable) == "a record the report cannot read"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
