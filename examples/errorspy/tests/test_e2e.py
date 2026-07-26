from __future__ import annotations

import json

from app.repository import StorageCampaignRepository
from app.service import CampaignService
from app.storage import FakeStorage
from transport.handler import Handler

_CREATE = json.dumps(
    {
        "window": {"start": "2026-01-01", "end": "2026-02-01"},
        "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
    }
)


def test_happy_path_create_get_add_deactivate() -> None:
    h = Handler(CampaignService(StorageCampaignRepository(FakeStorage())))
    assert h.create_campaign("c1", _CREATE).status == 201

    got = h.get_campaign("c1")
    assert got.status == 200
    assert got.body["links"] == ["spring-sale"]

    added = h.add_link("c1", json.dumps({"slug": "summer-sale", "target_url": "https://y.com"}))
    assert added.status == 200
    links = h.get_campaign("c1").body["links"]
    assert isinstance(links, list)
    assert sorted(str(x) for x in links) == ["spring-sale", "summer-sale"]

    off = h.deactivate_link("c1", "summer-sale")
    assert off.status == 200


def test_every_status_is_reachable_with_a_problem_body() -> None:
    h = Handler(CampaignService(StorageCampaignRepository(FakeStorage())))
    h.create_campaign("c1", _CREATE)

    seen: dict[int, str] = {}
    seen[400] = str(h.create_campaign("c2", "{bad").body["type"])
    seen[404] = str(h.get_campaign("missing").body["type"])
    seen[409] = str(
        h.add_link("c1", json.dumps({"slug": "spring-sale", "target_url": "https://z.com"})).body["type"]
    )
    seen[422] = str(
        h.add_link("c1", json.dumps({"slug": "BAD", "target_url": "ftp://n"})).body["type"]
    )
    down = Handler(CampaignService(StorageCampaignRepository(FakeStorage(down=True))))
    seen[503] = str(down.get_campaign("c1").body["type"])

    assert set(seen) == {400, 404, 409, 422, 503}
    assert all(t.startswith("/problems/") for t in seen.values())
