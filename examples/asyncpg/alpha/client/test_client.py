from __future__ import annotations

import alpha.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("empty_name", "a name is never empty")
        assert rejected.code == "empty_name"
        assert rejected.message == "a name is never empty"
        assert str(rejected) == "a name is never empty"


class TestMissing:

    def test_a_missing_carries_its_code_and_message(self) -> None:
        missing = client.Missing("unknown_widget", "no widget 'p'")
        assert missing.code == "unknown_widget"
        assert missing.message == "no widget 'p'"
        assert str(missing) == "no widget 'p'"


class TestConflict:

    def test_a_conflict_carries_its_code_and_message(self) -> None:
        conflict = client.Conflict("widget_exists", "widget 'p' is already stored")
        assert conflict.code == "widget_exists"
        assert conflict.message == "widget 'p' is already stored"
        assert str(conflict) == "widget 'p' is already stored"


class TestUnavailable:

    def test_an_unavailable_dependency_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the widget store is unavailable")
        assert unavailable.message == "the widget store is unavailable"
        assert str(unavailable) == "the widget store is unavailable"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
