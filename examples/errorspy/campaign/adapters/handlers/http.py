from __future__ import annotations

import json

import tesser.adapters as ts

import campaign.client as client
import protocol
import tesser.errors as errors


class Handler(ts.Handler):

    def __init__(self, campaign_client: client.CampaignClient) -> None:
        self._campaign_client = campaign_client

    def create_campaign(self, campaign_id: str, raw: str) -> protocol.Response:
        try:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise protocol.BadRequest(f"malformed JSON: {e}") from e
            if not isinstance(data, dict):
                raise protocol.BadRequest("expected a JSON object")
            body: dict[str, object] = data
            window_value = body.get("window")
            if not isinstance(window_value, dict):
                raise protocol.BadRequest("'window' must be an object")
            window: dict[str, object] = window_value
            links_value = body.get("links")
            if not isinstance(links_value, list):
                raise protocol.BadRequest("'links' must be an array")
            links: list[object] = links_value
            window_start = window.get("start")
            if not isinstance(window_start, str):
                raise protocol.BadRequest("expected a string field")
            window_end = window.get("end")
            if not isinstance(window_end, str):
                raise protocol.BadRequest("expected a string field")
            link_bodies: list[client.LinkBody] = []
            for link in links:
                if not isinstance(link, dict):
                    raise protocol.BadRequest("'link' must be an object")
                entry: dict[str, object] = link
                slug = entry.get("slug")
                if not isinstance(slug, str):
                    raise protocol.BadRequest("expected a string field")
                target_url = entry.get("target_url")
                if not isinstance(target_url, str):
                    raise protocol.BadRequest("expected a string field")
                link_bodies.append(client.LinkBody(slug=slug, target_url=target_url))
            self._campaign_client.create_campaign(
                client.CreateCampaignRequest(
                    campaign_id=campaign_id,
                    window_start=window_start,
                    window_end=window_end,
                    links=tuple(link_bodies),
                )
            )
            return protocol.Response(201, {"id": campaign_id})
        except protocol.BadRequest as e:
            return protocol.Response(
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
            return protocol.Response(status, problem)
        except errors.InfraError:
            return protocol.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return protocol.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def get_campaign(self, campaign_id: str) -> protocol.Response:
        try:
            campaign_view = self._campaign_client.get_campaign(
                client.GetCampaignRequest(campaign_id=campaign_id)
            )
            return protocol.Response(
                200,
                {"id": campaign_view.campaign_id, "links": list(campaign_view.links)},
            )
        except protocol.BadRequest as e:
            return protocol.Response(
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
            return protocol.Response(status, problem)
        except errors.InfraError:
            return protocol.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return protocol.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def add_link(self, campaign_id: str, raw: str) -> protocol.Response:
        try:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise protocol.BadRequest(f"malformed JSON: {e}") from e
            if not isinstance(data, dict):
                raise protocol.BadRequest("expected a JSON object")
            body: dict[str, object] = data
            slug = body.get("slug")
            if not isinstance(slug, str):
                raise protocol.BadRequest("expected a string field")
            target_url = body.get("target_url")
            if not isinstance(target_url, str):
                raise protocol.BadRequest("expected a string field")
            self._campaign_client.add_link(
                client.AddLinkRequest(
                    campaign_id=campaign_id,
                    slug=slug,
                    target_url=target_url,
                )
            )
            return protocol.Response(200, {"status": "added"})
        except protocol.BadRequest as e:
            return protocol.Response(
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
            return protocol.Response(status, problem)
        except errors.InfraError:
            return protocol.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return protocol.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )

    def deactivate_link(self, campaign_id: str, slug: str) -> protocol.Response:
        try:
            self._campaign_client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
            return protocol.Response(200, {"status": "deactivated"})
        except protocol.BadRequest as e:
            return protocol.Response(
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
            return protocol.Response(status, problem)
        except errors.InfraError:
            return protocol.Response(
                503,
                {
                    "type": "/problems/unavailable",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": "please retry",
                },
            )
        except Exception:
            return protocol.Response(
                500,
                {
                    "type": "/problems/internal",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "unexpected error",
                },
            )
