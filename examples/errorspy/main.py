"""A tiny runnable demo of the error-norms stack: wire transport -> service ->
domain -> repo -> storage, then drive a few requests and print each status and
RFC 9457 body. Run: ``python main.py``.
"""

from __future__ import annotations

import json

from app.repository import StorageCampaignRepository
from app.service import CampaignService
from app.storage import FakeStorage
from transport.handler import Handler, Response


def _show(label: str, resp: Response) -> None:
    print(f"{label}: {resp.status}  {json.dumps(resp.body)}")


def main() -> None:
    handler = Handler(CampaignService(StorageCampaignRepository(FakeStorage())))

    create = json.dumps(
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
        }
    )
    _show("create        ", handler.create_campaign("c1", create))
    _show("get           ", handler.get_campaign("c1"))
    _show("get missing   ", handler.get_campaign("nope"))
    _show(
        "dup link      ",
        handler.add_link("c1", json.dumps({"slug": "spring-sale", "target_url": "https://y.com"})),
    )
    _show(
        "both bad      ",
        handler.add_link("c1", json.dumps({"slug": "BAD", "target_url": "ftp://n"})),
    )
    _show("malformed     ", handler.create_campaign("c2", "{not json"))


if __name__ == "__main__":
    main()
