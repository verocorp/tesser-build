from __future__ import annotations

import campaign.client as client


class TestCampaignRejected:

    def test_a_rejected_campaign_carries_its_code_and_message(self) -> None:
        campaign_rejected = client.CampaignRejected(
            "invalid_budget_amount", "budget amount '-5' is not a number"
        )
        assert campaign_rejected.code == "invalid_budget_amount"
        assert campaign_rejected.message == "budget amount '-5' is not a number"
        assert str(campaign_rejected) == "budget amount '-5' is not a number"


class TestCampaignNotFound:

    def test_a_campaign_that_was_not_found_carries_its_message(self) -> None:
        campaign_not_found = client.CampaignNotFound("no campaign with id 'fedcba9876543210'")
        assert campaign_not_found.message == "no campaign with id 'fedcba9876543210'"
        assert str(campaign_not_found) == "no campaign with id 'fedcba9876543210'"


class TestLinkNotFound:

    def test_a_link_that_was_not_found_carries_its_message(self) -> None:
        link_not_found = client.LinkNotFound("no active link for slug 'promo'")
        assert link_not_found.message == "no active link for slug 'promo'"
        assert str(link_not_found) == "no active link for slug 'promo'"


class TestSlugTaken:

    def test_a_taken_slug_carries_its_message(self) -> None:
        slug_taken = client.SlugTaken("slug 'promo' already exists")
        assert slug_taken.message == "slug 'promo' already exists"
        assert str(slug_taken) == "slug 'promo' already exists"


class TestTargetBlocked:

    def test_a_blocked_target_carries_its_message(self) -> None:
        target_blocked = client.TargetBlocked("destination not allowed: on the deny-list")
        assert target_blocked.message == "destination not allowed: on the deny-list"
        assert str(target_blocked) == "destination not allowed: on the deny-list"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
