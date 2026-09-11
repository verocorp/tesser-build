from __future__ import annotations

import ordering.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("order_rejected", "an order is for at least one unit")
        assert rejected.code == "order_rejected"
        assert rejected.message == "an order is for at least one unit"
        assert str(rejected) == "an order is for at least one unit"


class TestMissing:

    def test_a_missing_carries_its_code_and_message(self) -> None:
        missing = client.Missing("order_rejected", "no price for sku 'nope'")
        assert missing.code == "order_rejected"
        assert missing.message == "no price for sku 'nope'"
        assert str(missing) == "no price for sku 'nope'"


class TestConflict:

    def test_a_conflict_carries_its_code_and_message(self) -> None:
        conflict = client.Conflict("order_rejected", "the order is already running")
        assert conflict.code == "order_rejected"
        assert conflict.message == "the order is already running"
        assert str(conflict) == "the order is already running"


class TestUnavailable:

    def test_an_unavailable_engine_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the ordering engine is unavailable")
        assert unavailable.message == "the ordering engine is unavailable"
        assert str(unavailable) == "the ordering engine is unavailable"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
