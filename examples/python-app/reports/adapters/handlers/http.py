from __future__ import annotations

from httpwire import JSONObject, Response, respond
from reports.client import Client, LinkVerdictView


class Handler:
    def __init__(self, client: Client) -> None:
        self._client = client

    def links_by_verdict(self) -> Response:
        def run() -> Response:
            rows = [_row(view) for view in self._client.links_by_verdict()]
            return Response(200, {"links": rows})

        return respond(run)


def _row(view: LinkVerdictView) -> JSONObject:
    return {
        "slug": view.slug,
        "target_url": view.target_url,
        "allowed": view.allowed,
        "reason": view.reason,
    }
