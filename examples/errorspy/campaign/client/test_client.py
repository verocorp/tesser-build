from __future__ import annotations

import campaign.client as client


class TestCampaignRejected:

    def test_a_rejected_campaign_carries_its_code_message_field_and_problems(self) -> None:
        campaign_rejected = client.CampaignRejected(
            client.Rejection(
                "bad_slug",
                "invalid slug 'BAD'",
                "links[0].slug",
                (client.Problem("bad_slug", "slug", "invalid slug 'BAD'"),),
            )
        )
        assert campaign_rejected.rejection.code == "bad_slug"
        assert campaign_rejected.rejection.message == "invalid slug 'BAD'"
        assert campaign_rejected.rejection.field == "links[0].slug"
        assert campaign_rejected.rejection.problems[0].field == "slug"
        assert str(campaign_rejected) == "invalid slug 'BAD'"


class TestCampaignNotFound:

    def test_a_campaign_that_was_not_found_carries_its_message(self) -> None:
        campaign_not_found = client.CampaignNotFound("no campaign 'nope'")
        assert campaign_not_found.message == "no campaign 'nope'"
        assert str(campaign_not_found) == "no campaign 'nope'"


class TestLinkNotAdded:

    def test_a_link_that_was_not_added_carries_its_code_and_message(self) -> None:
        link_not_added = client.LinkNotAdded("duplicate_slug", "slug spring-sale already in c1")
        assert link_not_added.code == "duplicate_slug"
        assert link_not_added.message == "slug spring-sale already in c1"
        assert str(link_not_added) == "slug spring-sale already in c1"


class TestLinkNotDeactivated:

    def test_a_link_that_was_not_deactivated_carries_its_code_and_message(self) -> None:
        link_not_deactivated = client.LinkNotDeactivated("link_missing", "no link 'ghost-link'")
        assert link_not_deactivated.code == "link_missing"
        assert link_not_deactivated.message == "no link 'ghost-link'"
        assert str(link_not_deactivated) == "no link 'ghost-link'"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
