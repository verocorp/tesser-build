from __future__ import annotations

import tesser.adapters as ts

from httpwire import HttpRequest, JSONObject, HttpResponse
from reports.client import Client, LinksByVerdictRequest, LinkVerdictView


class Handler(ts.Handler):
    def __init__(self, client: Client) -> None:
        self._client = client

    def links_by_verdict(self, _req: HttpRequest) -> HttpResponse:
        def run() -> HttpResponse:
            resp = self._client.links_by_verdict(LinksByVerdictRequest())
            rows = [_row(view) for view in resp.links]
            return HttpResponse.json(200, {"links": rows})

        return HttpResponse.respond(run)


@ts.function
def _row(view: LinkVerdictView) -> JSONObject:
    return {
        "slug": view.slug,
        "target_url": view.target_url,
        "allowed": view.allowed,
        "reason": view.reason,
    }
