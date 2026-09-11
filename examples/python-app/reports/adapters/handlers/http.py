from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol as protocol
import reports.client as client


class HttpHandler(ts.Handler):
    def __init__(self, reports_client: client.ReportsClient) -> None:
        self._reports_client = reports_client

    def links_by_verdict(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            links_by_verdict_response = self._reports_client.links_by_verdict(
                client.LinksByVerdictRequest()
            )
        except client.ERRORS as error:
            match error:
                case client.Unavailable():
                    return protocol.HttpResponse.problem(503, "unavailable", error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        rows: list[dict[str, object]] = [
            {
                "slug": view.slug,
                "target_url": view.target_url,
                "decision": view.decision,
                "reason": view.reason,
            }
            for view in links_by_verdict_response.links
        ]
        return protocol.HttpResponse.json(200, {"links": rows})
