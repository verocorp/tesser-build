from __future__ import annotations

import campaign.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_message_field_and_problems(self) -> None:
        rejected = client.Rejected(
            client.Rejection(
                "bad_slug",
                "invalid slug 'BAD'",
                "links[0].slug",
                (client.Problem("bad_slug", "slug", "invalid slug 'BAD'"),),
            )
        )
        assert rejected.rejection.code == "bad_slug"
        assert rejected.rejection.message == "invalid slug 'BAD'"
        assert rejected.rejection.field == "links[0].slug"
        assert rejected.rejection.problems[0].field == "slug"
        assert str(rejected) == "invalid slug 'BAD'"


class TestMissing:

    def test_a_missing_carries_its_code_and_message(self) -> None:
        missing = client.Missing("campaign_missing", "no campaign 'nope'")
        assert missing.code == "campaign_missing"
        assert missing.message == "no campaign 'nope'"
        assert str(missing) == "no campaign 'nope'"


class TestConflict:

    def test_a_conflict_carries_its_code_and_message(self) -> None:
        conflict = client.Conflict("duplicate_slug", "slug spring-sale already in c1")
        assert conflict.code == "duplicate_slug"
        assert conflict.message == "slug spring-sale already in c1"
        assert str(conflict) == "slug spring-sale already in c1"


class TestUnavailable:

    def test_an_unavailable_store_carries_its_message(self) -> None:
        unavailable = client.Unavailable("campaign storage cannot answer for 'c1'")
        assert unavailable.message == "campaign storage cannot answer for 'c1'"
        assert str(unavailable) == "campaign storage cannot answer for 'c1'"


class TestUnreadable:

    def test_an_unreadable_record_carries_its_message(self) -> None:
        unreadable = client.Unreadable("corrupted campaign record 'c1'")
        assert unreadable.message == "corrupted campaign record 'c1'"
        assert str(unreadable) == "corrupted campaign record 'c1'"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
