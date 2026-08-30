from __future__ import annotations

import tesser.adapters as ts

import protocol.http as http
import reports.client.client as client


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def links_by_verdict(self, _req: http.HttpRequest) -> http.HttpResponse:
        resp = self._client.links_by_verdict(client.LinksByVerdictRequest())
        rows: list[dict[str, object]] = [
            {
                "slug": view.slug,
                "target_url": view.target_url,
                "decision": view.decision,
                "reason": view.reason,
            }
            for view in resp.links
        ]
        return http.HttpResponse.json(200, {"links": rows})
