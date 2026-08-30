from __future__ import annotations

import json

import tesser.adapters as ts

import campaign.client.client as client
import protocol.http as http
import tesser.errors as errors


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def create_campaign(self, campaign_id: str, raw: str) -> http.Response:
        try:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise http.BadRequest(f"malformed JSON: {e}") from e
            if not isinstance(data, dict):
                raise http.BadRequest("expected a JSON object")
            body: dict[str, object] = data
            window_value = body.get("window")
            if not isinstance(window_value, dict):
                raise http.BadRequest("'window' must be an object")
            window: dict[str, object] = window_value
            links_value = body.get("links")
            if not isinstance(links_value, list):
                raise http.BadRequest("'links' must be an array")
            links: list[object] = links_value
            window_start = window.get("start")
            if not isinstance(window_start, str):
                raise http.BadRequest("expected a string field")
            window_end = window.get("end")
            if not isinstance(window_end, str):
                raise http.BadRequest("expected a string field")
            link_bodies: list[client.LinkBody] = []
            for link in links:
                if not isinstance(link, dict):
                    raise http.BadRequest("'link' must be an object")
                entry: dict[str, object] = link
                slug = entry.get("slug")
                if not isinstance(slug, str):
                    raise http.BadRequest("expected a string field")
                target_url = entry.get("target_url")
                if not isinstance(target_url, str):
                    raise http.BadRequest("expected a string field")
                link_bodies.append(client.LinkBody(slug=slug, target_url=target_url))
            self._client.create_campaign(
                client.CreateCampaignRequest(
                    campaign_id=campaign_id,
                    window_start=window_start,
                    window_end=window_end,
                    links=tuple(link_bodies),
                )
            )
            return http.Response(201, {"id": campaign_id})
        except http.BadRequest as e:
            return http.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(e),
                },
            )
        except errors.DomainError as e:
            status = errors.status_for(e.kind)
            problem: dict[str, object] = {
                "type": f"/problems/{e.code}",
                "title": e.code.replace("_", " "),
                "status": status,
                "detail": e.message,
            }
            if e.field is not None:
                problem["field"] = e.field
            if e.problems:
                problem["invalid-params"] = [
                    {"name": p.field, "code": p.code, "reason": p.message}
                    for p in e.problems
                ]
            return http.Response(status, problem)
        except errors.InfraError:
            return http.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return http.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def get_campaign(self, campaign_id: str) -> http.Response:
        try:
            view = self._client.get_campaign(
                client.GetCampaignRequest(campaign_id=campaign_id)
            )
            return http.Response(200, {"id": view.campaign_id, "links": list(view.links)})
        except http.BadRequest as e:
            return http.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(e),
                },
            )
        except errors.DomainError as e:
            status = errors.status_for(e.kind)
            problem: dict[str, object] = {
                "type": f"/problems/{e.code}",
                "title": e.code.replace("_", " "),
                "status": status,
                "detail": e.message,
            }
            if e.field is not None:
                problem["field"] = e.field
            if e.problems:
                problem["invalid-params"] = [
                    {"name": p.field, "code": p.code, "reason": p.message}
                    for p in e.problems
                ]
            return http.Response(status, problem)
        except errors.InfraError:
            return http.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return http.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def add_link(self, campaign_id: str, raw: str) -> http.Response:
        try:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise http.BadRequest(f"malformed JSON: {e}") from e
            if not isinstance(data, dict):
                raise http.BadRequest("expected a JSON object")
            body: dict[str, object] = data
            slug = body.get("slug")
            if not isinstance(slug, str):
                raise http.BadRequest("expected a string field")
            target_url = body.get("target_url")
            if not isinstance(target_url, str):
                raise http.BadRequest("expected a string field")
            self._client.add_link(
                client.AddLinkRequest(
                    campaign_id=campaign_id,
                    slug=slug,
                    target_url=target_url,
                )
            )
            return http.Response(200, {"status": "added"})
        except http.BadRequest as e:
            return http.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(e),
                },
            )
        except errors.DomainError as e:
            status = errors.status_for(e.kind)
            problem: dict[str, object] = {
                "type": f"/problems/{e.code}",
                "title": e.code.replace("_", " "),
                "status": status,
                "detail": e.message,
            }
            if e.field is not None:
                problem["field"] = e.field
            if e.problems:
                problem["invalid-params"] = [
                    {"name": p.field, "code": p.code, "reason": p.message}
                    for p in e.problems
                ]
            return http.Response(status, problem)
        except errors.InfraError:
            return http.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return http.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def deactivate_link(self, campaign_id: str, slug: str) -> http.Response:
        try:
            self._client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
            return http.Response(200, {"status": "deactivated"})
        except http.BadRequest as e:
            return http.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(e),
                },
            )
        except errors.DomainError as e:
            status = errors.status_for(e.kind)
            problem: dict[str, object] = {
                "type": f"/problems/{e.code}",
                "title": e.code.replace("_", " "),
                "status": status,
                "detail": e.message,
            }
            if e.field is not None:
                problem["field"] = e.field
            if e.problems:
                problem["invalid-params"] = [
                    {"name": p.field, "code": p.code, "reason": p.message}
                    for p in e.problems
                ]
            return http.Response(status, problem)
        except errors.InfraError:
            return http.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return http.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )
