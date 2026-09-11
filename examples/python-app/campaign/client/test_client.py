from __future__ import annotations

import campaign.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("invalid_budget_amount", "budget amount '-5' is not a number")
        assert rejected.code == "invalid_budget_amount"
        assert rejected.message == "budget amount '-5' is not a number"
        assert str(rejected) == "budget amount '-5' is not a number"


class TestMissing:

    def test_a_missing_carries_its_code_and_message(self) -> None:
        missing = client.Missing("campaign_missing", "no campaign with id 'fedcba9876543210'")
        assert missing.code == "campaign_missing"
        assert missing.message == "no campaign with id 'fedcba9876543210'"
        assert str(missing) == "no campaign with id 'fedcba9876543210'"


class TestConflict:

    def test_a_conflict_carries_its_code_and_message(self) -> None:
        conflict = client.Conflict("duplicate_slug", "duplicate slug promo in campaign")
        assert conflict.code == "duplicate_slug"
        assert conflict.message == "duplicate slug promo in campaign"
        assert str(conflict) == "duplicate slug promo in campaign"


class TestUnreadable:

    def test_an_unreadable_record_carries_its_message(self) -> None:
        unreadable = client.Unreadable("stored campaign '0123456789abcdef' cannot be read back")
        assert unreadable.message == "stored campaign '0123456789abcdef' cannot be read back"
        assert str(unreadable) == "stored campaign '0123456789abcdef' cannot be read back"


class TestUnavailable:

    def test_an_unavailable_dependency_carries_its_message(self) -> None:
        unavailable = client.Unavailable("the campaign store is unavailable")
        assert unavailable.message == "the campaign store is unavailable"
        assert str(unavailable) == "the campaign store is unavailable"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
