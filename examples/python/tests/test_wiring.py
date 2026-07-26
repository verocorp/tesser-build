import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from campaignapp import CampaignService
from linkcampaign import Client
from linkcampaignimpl import new_client
from main import wire
from transport import make_handler


@pytest.fixture()
def base_url() -> Iterator[str]:
    server = wire(("127.0.0.1", 0))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join()


def test_end_to_end_create_get_add_deactivate(base_url: str) -> None:
    create = urllib.request.Request(
        f"{base_url}/campaigns",
        data=json.dumps(
            {
                "name": "Spring",
                "links": [{"slug": "spring-sale", "target_url": "https://a.example"}],
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(create) as resp:
        assert resp.status == 201
        created = json.loads(resp.read())
    cid = created["campaign_id"]
    assert created["name"] == "Spring"

    get = urllib.request.Request(
        f"{base_url}/campaigns/{cid}",
        method="GET",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(get) as resp:
        assert resp.status == 200
        got = json.loads(resp.read())
    assert {l["slug"] for l in got["links"]} == {"spring-sale"}

    add = urllib.request.Request(
        f"{base_url}/campaigns/{cid}/links",
        data=json.dumps(
            {"slug": "autumn-sale", "target_url": "https://b.example"}
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(add) as resp:
        assert resp.status == 200
        added = json.loads(resp.read())
    assert {l["slug"] for l in added["links"]} == {"spring-sale", "autumn-sale"}

    deactivate = urllib.request.Request(
        f"{base_url}/campaigns/{cid}/links/spring-sale/deactivate",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(deactivate) as resp:
        assert resp.status == 200
        deactivated = json.loads(resp.read())
    by_slug = {l["slug"]: l for l in deactivated["links"]}
    assert by_slug["spring-sale"]["active"] is False
    assert by_slug["autumn-sale"]["active"] is True


def test_domain_rule_rejected_end_to_end(base_url: str) -> None:
    request = urllib.request.Request(
        f"{base_url}/campaigns",
        data=json.dumps(
            {
                "name": "Spring",
                "links": [{"slug": "X", "target_url": "https://a.example"}],
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 422
    assert "invalid" in json.loads(caught.value.read())["error"]


def test_no_domain_object_leaks_across_the_boundary(base_url: str) -> None:
    request = urllib.request.Request(
        f"{base_url}/campaigns",
        data=json.dumps(
            {
                "name": "Spring",
                "links": [{"slug": "spring-sale", "target_url": "https://a.example"}],
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as resp:
        created = json.loads(resp.read())
    assert set(created.keys()) == {"campaign_id", "name", "links"}
    for view in created["links"]:
        assert set(view.keys()) == {"slug", "target_url", "active"}
        assert isinstance(view["slug"], str)
        assert isinstance(view["active"], bool)


class _NullRepo:

    def save(self, c: object) -> None:
        pass

    def load(self, id: object) -> Any:
        raise LookupError("empty")


def test_repository_is_substitutable_at_the_composition_seam() -> None:
    client: Client = new_client(CampaignService(_NullRepo()))
    handler_cls = make_handler(client)
    assert handler_cls is not None
    for method in ("create_campaign", "add_short_link", "deactivate_short_link", "get_campaign"):
        assert callable(getattr(client, method))
