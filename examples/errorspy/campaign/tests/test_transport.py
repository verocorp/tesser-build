from __future__ import annotations

import json

import campaign.adapters.handlers as handlers
import campaign.adapters.repositories as repositories
import campaign.application as application
import storage


def test_create_valid_is_201() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    body = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
        }
    )

    assert handler.create_campaign("c1", body).status == 201


def test_validation_is_422_with_rfc9457_body() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    bad = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD", "target_url": "https://x.com"}],
        }
    )

    response = handler.create_campaign("c1", bad)

    assert response.status == 422
    assert response.body["type"] == "/problems/bad_slug"
    assert response.body["status"] == 422
    assert response.body["field"] == "links[0].slug"


def test_not_found_is_404() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )

    response = handler.get_campaign("nope")

    assert response.status == 404
    assert response.body["type"] == "/problems/campaign_missing"


def test_conflict_is_409() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    handler.create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    dup = json.dumps({"slug": "spring-sale", "target_url": "https://y.com"})

    response = handler.add_link("c1", dup)

    assert response.status == 409
    assert response.body["type"] == "/problems/duplicate_slug"


def test_two_identical_slugs_in_one_create_body_is_422_not_409() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    body = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [
                {"slug": "spring-sale", "target_url": "https://x.com"},
                {"slug": "spring-sale", "target_url": "https://y.com"},
            ],
        }
    )

    response = handler.create_campaign("c1", body)

    assert response.status == 422
    assert response.body["type"] == "/problems/duplicate_slug"


def test_malformed_json_is_400_not_422() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )

    response = handler.create_campaign("c1", "{not json")

    assert response.status == 400
    assert response.body["type"] == "/problems/malformed_request"


def test_aggregated_validation_lists_all_invalid_params() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    handler.create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    both_bad = json.dumps({"slug": "BAD", "target_url": "ftp://nope"})

    response = handler.add_link("c1", both_bad)

    assert response.status == 422
    assert response.body["type"] == "/problems/validation_failed"
    params = response.body["invalid-params"]
    assert isinstance(params, list)
    codes = {p["code"] for p in params}
    assert codes == {"bad_slug", "bad_target_url"}


def test_an_unavailable_store_is_503() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage(down=True))
        )
    )

    response = handler.get_campaign("c1")

    assert response.status == 503
    assert response.body["type"] == "/problems/unavailable"
