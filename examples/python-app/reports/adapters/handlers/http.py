from __future__ import annotations

import tesser.adapters as ts

from protocol.http import HttpRequest, JSONObject, HttpResponse
import reports.client.client as client


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def links_by_verdict(self, _req: HttpRequest) -> HttpResponse:
        resp = self._client.links_by_verdict(client.LinksByVerdictRequest())
        rows = [_row(view) for view in resp.links]
        return HttpResponse.json(200, {"links": rows})


@ts.do_not_use_function
def _row(view: client.LinkVerdictView) -> JSONObject:  # tesser:debt TB051
    return {
        "slug": view.slug,
        "target_url": view.target_url,
        "allowed": view.allowed,
        "reason": view.reason,
    }
