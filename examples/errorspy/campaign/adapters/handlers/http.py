from __future__ import annotations

from collections.abc import Callable

import tesser.adapters as ts

import campaign.client.client as client
import protocol.http as http
from tesser.errors import DomainError, InfraError, status_for


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def create_campaign(self, campaign_id: str, raw: str) -> http.Response:
        def run() -> http.Response:
            body = http.json_object(raw)
            window = http.object_field(body.get("window"), "window")
            links = http.array_field(body.get("links"), "links")
            self._client.create_campaign(
                client.CreateCampaignRequest(
                    campaign_id=campaign_id,
                    window_start=http.string_field(window.get("start")),
                    window_end=http.string_field(window.get("end")),
                    links=tuple(_link_body(link) for link in links),
                )
            )
            return http.Response(201, {"id": campaign_id})

        return self._respond(run)

    def get_campaign(self, campaign_id: str) -> http.Response:
        def run() -> http.Response:
            view = self._client.get_campaign(
                client.GetCampaignRequest(campaign_id=campaign_id)
            )
            return http.Response(200, {"id": view.campaign_id, "links": list(view.links)})

        return self._respond(run)

    def add_link(self, campaign_id: str, raw: str) -> http.Response:
        def run() -> http.Response:
            body = http.json_object(raw)
            self._client.add_link(
                client.AddLinkRequest(
                    campaign_id=campaign_id,
                    slug=http.string_field(body.get("slug")),
                    target_url=http.string_field(body.get("target_url")),
                )
            )
            return http.Response(200, {"status": "added"})

        return self._respond(run)

    def deactivate_link(self, campaign_id: str, slug: str) -> http.Response:
        def run() -> http.Response:
            self._client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
            return http.Response(200, {"status": "deactivated"})

        return self._respond(run)

    def _respond(self, run: Callable[[], http.Response]) -> http.Response:  # tesser:debt TB051
        try:
            return run()
        except http.BadRequest as e:
            return http.Response(400, _problem("malformed_request", "Bad Request", 400, str(e)))
        except DomainError as e:
            status = status_for(e.kind)
            return http.Response(status, _problem_for(e, status))
        except InfraError:
            return http.Response(
                503, _problem("unavailable", "Service Unavailable", 503, "please retry")
            )
        except Exception:  # noqa: BLE001 — the unexpected-500 backstop
            return http.Response(
                500, _problem("internal", "Internal Server Error", 500, "unexpected error")
            )


@ts.do_not_use_function
def _link_body(value: object) -> client.LinkBody:  # tesser:debt TB051
    link = http.object_field(value, "link")
    return client.LinkBody(
        slug=http.string_field(link.get("slug")),
        target_url=http.string_field(link.get("target_url")),
    )


@ts.do_not_use_function
def _problem(code: str, title: str, status: int, detail: str) -> http.JSONObject:  # tesser:debt TB051
    return {
        "type": f"/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
    }


@ts.do_not_use_function
def _problem_for(err: DomainError, status: int) -> http.JSONObject:  # tesser:debt TB051
    body = _problem(err.code, err.code.replace("_", " "), status, err.message)
    if err.field is not None:
        body["field"] = err.field
    if err.problems:
        body["invalid-params"] = [
            {"name": p.field, "code": p.code, "reason": p.message}
            for p in err.problems
        ]
    return body
