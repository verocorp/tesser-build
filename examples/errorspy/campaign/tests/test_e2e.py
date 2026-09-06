from __future__ import annotations

import json

import campaign.adapters.handlers as handlers
import campaign.adapters.repositories as repositories
import campaign.application as application
import storage


def test_happy_path_create_get_add_deactivate() -> None:
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

    got = handler.get_campaign("c1")
    assert got.status == 200
    assert got.body["links"] == ["spring-sale"]

    added = handler.add_link(
        "c1", json.dumps({"slug": "summer-sale", "target_url": "https://y.com"})
    )
    assert added.status == 200
    links = handler.get_campaign("c1").body["links"]
    assert isinstance(links, list)
    assert sorted(str(x) for x in links) == ["spring-sale", "summer-sale"]

    off = handler.deactivate_link("c1", "summer-sale")
    assert off.status == 200


def test_every_status_is_reachable_with_a_problem_body() -> None:
    handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage())
        )
    )
    down_handler = handlers.Handler(
        application.CampaignService(
            repositories.StorageCampaignRepository(storage.FakeStorage(down=True))
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

    seen: dict[int, str] = {}
    seen[400] = str(handler.create_campaign("c2", "{bad").body["type"])
    seen[404] = str(handler.get_campaign("missing").body["type"])
    seen[409] = str(
        handler.add_link(
            "c1", json.dumps({"slug": "spring-sale", "target_url": "https://z.com"})
        ).body["type"]
    )
    seen[422] = str(
        handler.add_link("c1", json.dumps({"slug": "BAD", "target_url": "ftp://n"})).body[
            "type"
        ]
    )
    seen[503] = str(down_handler.get_campaign("c1").body["type"])

    assert set(seen) == {400, 404, 409, 422, 503}
    assert all(t.startswith("/problems/") for t in seen.values())
