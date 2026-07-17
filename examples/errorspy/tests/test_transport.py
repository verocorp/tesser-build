"""Cells B3 (kind -> status via the pure mapper), B4 (RFC 9457 body with type +
field), B5 (malformed request -> 400, not 422), B6 (aggregated multi-field
validation), plus the InfraError -> 503 path."""

from __future__ import annotations

import json

from app.repository import StorageCampaignRepository
from app.service import CampaignService
from app.storage import FakeStorage
from transport.handler import Handler

_VALID_CREATE = json.dumps(
    {
        "window": {"start": "2026-01-01", "end": "2026-02-01"},
        "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
    }
)


def _handler(*, down: bool = False) -> Handler:
    repo = StorageCampaignRepository(FakeStorage(down=down))
    return Handler(CampaignService(repo))


def test_create_valid_is_201() -> None:
    assert _handler().create_campaign("c1", _VALID_CREATE).status == 201


def test_validation_is_422_with_rfc9457_body() -> None:
    # B3 + B4: a bad slug -> 422, body carries the code as `type` and the field.
    bad = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD", "target_url": "https://x.com"}],
        }
    )
    resp = _handler().create_campaign("c1", bad)
    assert resp.status == 422
    assert resp.body["type"] == "/problems/bad_slug"
    assert resp.body["status"] == 422
    assert resp.body["field"] == "links[0].slug"


def test_not_found_is_404() -> None:
    # B3: kind=not_found -> 404, through the same pure mapper.
    resp = _handler().get_campaign("nope")
    assert resp.status == 404
    assert resp.body["type"] == "/problems/campaign_missing"


def test_conflict_is_409() -> None:
    h = _handler()
    h.create_campaign("c1", _VALID_CREATE)
    dup = json.dumps({"slug": "spring-sale", "target_url": "https://y.com"})
    resp = h.add_link("c1", dup)
    assert resp.status == 409
    assert resp.body["type"] == "/problems/duplicate_slug"


def test_malformed_json_is_400_not_422() -> None:
    # B5: a parse failure is a transport concern (400), never domain validation.
    resp = _handler().create_campaign("c1", "{not json")
    assert resp.status == 400
    assert resp.body["type"] == "/problems/malformed_request"


def test_aggregated_validation_lists_all_invalid_params() -> None:
    # B6: both fields bad -> one 422 carrying every failure in invalid-params.
    h = _handler()
    h.create_campaign("c1", _VALID_CREATE)
    both_bad = json.dumps({"slug": "BAD", "target_url": "ftp://nope"})
    resp = h.add_link("c1", both_bad)
    assert resp.status == 422
    assert resp.body["type"] == "/problems/validation_failed"
    params = resp.body["invalid-params"]
    assert isinstance(params, list)
    codes = {p["code"] for p in params}
    assert codes == {"bad_slug", "bad_target_url"}


def test_infra_is_503() -> None:
    resp = _handler(down=True).get_campaign("c1")
    assert resp.status == 503
    assert resp.body["type"] == "/problems/unavailable"
