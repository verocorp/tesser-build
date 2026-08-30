from __future__ import annotations

import json

import campaign.adapters.repositories.repo_storage as repo_storage
import campaign.adapters.handlers.http as handlers
import campaign.application.service as service
import storage


def test_create_valid_is_201() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))
    body = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
        }
    )

    assert h.create_campaign("c1", body).status == 201


def test_validation_is_422_with_rfc9457_body() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))
    bad = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD", "target_url": "https://x.com"}],
        }
    )

    resp = h.create_campaign("c1", bad)

    assert resp.status == 422
    assert resp.body["type"] == "/problems/bad_slug"
    assert resp.body["status"] == 422
    assert resp.body["field"] == "links[0].slug"


def test_not_found_is_404() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))

    resp = h.get_campaign("nope")

    assert resp.status == 404
    assert resp.body["type"] == "/problems/campaign_missing"


def test_conflict_is_409() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))
    h.create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    dup = json.dumps({"slug": "spring-sale", "target_url": "https://y.com"})

    resp = h.add_link("c1", dup)

    assert resp.status == 409
    assert resp.body["type"] == "/problems/duplicate_slug"


def test_malformed_json_is_400_not_422() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))

    resp = h.create_campaign("c1", "{not json")

    assert resp.status == 400
    assert resp.body["type"] == "/problems/malformed_request"


def test_aggregated_validation_lists_all_invalid_params() -> None:
    h = handlers.Handler(service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage())))
    h.create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    both_bad = json.dumps({"slug": "BAD", "target_url": "ftp://nope"})

    resp = h.add_link("c1", both_bad)

    assert resp.status == 422
    assert resp.body["type"] == "/problems/validation_failed"
    params = resp.body["invalid-params"]
    assert isinstance(params, list)
    codes = {p["code"] for p in params}
    assert codes == {"bad_slug", "bad_target_url"}


def test_infra_is_503() -> None:
    h = handlers.Handler(
        service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage(down=True)))
    )

    resp = h.get_campaign("c1")

    assert resp.status == 503
    assert resp.body["type"] == "/problems/unavailable"
