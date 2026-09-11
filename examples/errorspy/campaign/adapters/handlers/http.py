from __future__ import annotations

import json
import typing

import tesser.adapters as ts

import campaign.client as client
import protocol

_UNAVAILABLE: typing.Final[dict[str, object]] = {
    "type": "/problems/unavailable",
    "title": "Service Unavailable",
    "status": 503,
    "detail": "please retry",
}


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
        except protocol.BadRequest as bad_request:
            return protocol.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(bad_request),
                },
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    rejection = error.rejection
                    problem: dict[str, object] = {
                        "type": f"/problems/{rejection.code}",
                        "title": rejection.code.replace("_", " "),
                        "status": 422,
                        "detail": rejection.message,
                    }
                    if rejection.field:
                        problem["field"] = rejection.field
                    if rejection.problems:
                        problem["invalid-params"] = [
                            {
                                "name": reported.field,
                                "code": reported.code,
                                "reason": reported.message,
                            }
                            for reported in rejection.problems
                        ]
                    return protocol.Response(422, problem)
                case client.Missing():
                    return protocol.Response(
                        404,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 404,
                            "detail": error.message,
                        },
                    )
                case client.Conflict():
                    return protocol.Response(
                        409,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 409,
                            "detail": error.message,
                        },
                    )
                case client.Unavailable():
                    return protocol.Response(503, _UNAVAILABLE)
                case client.Unreadable():
                    return protocol.Response(503, _UNAVAILABLE)
                case _ as never:
                    typing.assert_never(never)
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
        return protocol.Response(201, {"id": campaign_id})

    def get_campaign(self, campaign_id: str) -> protocol.Response:
        try:
            campaign_view = self._campaign_client.get_campaign(
                client.GetCampaignRequest(campaign_id=campaign_id)
            )
        except protocol.BadRequest as bad_request:
            return protocol.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(bad_request),
                },
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    rejection = error.rejection
                    problem: dict[str, object] = {
                        "type": f"/problems/{rejection.code}",
                        "title": rejection.code.replace("_", " "),
                        "status": 422,
                        "detail": rejection.message,
                    }
                    if rejection.field:
                        problem["field"] = rejection.field
                    if rejection.problems:
                        problem["invalid-params"] = [
                            {
                                "name": reported.field,
                                "code": reported.code,
                                "reason": reported.message,
                            }
                            for reported in rejection.problems
                        ]
                    return protocol.Response(422, problem)
                case client.Missing():
                    return protocol.Response(
                        404,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 404,
                            "detail": error.message,
                        },
                    )
                case client.Conflict():
                    return protocol.Response(
                        409,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 409,
                            "detail": error.message,
                        },
                    )
                case client.Unavailable():
                    return protocol.Response(503, _UNAVAILABLE)
                case client.Unreadable():
                    return protocol.Response(503, _UNAVAILABLE)
                case _ as never:
                    typing.assert_never(never)
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
        return protocol.Response(
            200,
            {"id": campaign_view.campaign_id, "links": list(campaign_view.links)},
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
        except protocol.BadRequest as bad_request:
            return protocol.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(bad_request),
                },
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    rejection = error.rejection
                    problem: dict[str, object] = {
                        "type": f"/problems/{rejection.code}",
                        "title": rejection.code.replace("_", " "),
                        "status": 422,
                        "detail": rejection.message,
                    }
                    if rejection.field:
                        problem["field"] = rejection.field
                    if rejection.problems:
                        problem["invalid-params"] = [
                            {
                                "name": reported.field,
                                "code": reported.code,
                                "reason": reported.message,
                            }
                            for reported in rejection.problems
                        ]
                    return protocol.Response(422, problem)
                case client.Missing():
                    return protocol.Response(
                        404,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 404,
                            "detail": error.message,
                        },
                    )
                case client.Conflict():
                    return protocol.Response(
                        409,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 409,
                            "detail": error.message,
                        },
                    )
                case client.Unavailable():
                    return protocol.Response(503, _UNAVAILABLE)
                case client.Unreadable():
                    return protocol.Response(503, _UNAVAILABLE)
                case _ as never:
                    typing.assert_never(never)
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
        return protocol.Response(200, {"status": "added"})

    def deactivate_link(self, campaign_id: str, slug: str) -> protocol.Response:
        try:
            self._campaign_client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
        except protocol.BadRequest as bad_request:
            return protocol.Response(
                400,
                {
                    "type": "/problems/malformed_request",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": str(bad_request),
                },
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    rejection = error.rejection
                    problem: dict[str, object] = {
                        "type": f"/problems/{rejection.code}",
                        "title": rejection.code.replace("_", " "),
                        "status": 422,
                        "detail": rejection.message,
                    }
                    if rejection.field:
                        problem["field"] = rejection.field
                    if rejection.problems:
                        problem["invalid-params"] = [
                            {
                                "name": reported.field,
                                "code": reported.code,
                                "reason": reported.message,
                            }
                            for reported in rejection.problems
                        ]
                    return protocol.Response(422, problem)
                case client.Missing():
                    return protocol.Response(
                        404,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 404,
                            "detail": error.message,
                        },
                    )
                case client.Conflict():
                    return protocol.Response(
                        409,
                        {
                            "type": f"/problems/{error.code}",
                            "title": error.code.replace("_", " "),
                            "status": 409,
                            "detail": error.message,
                        },
                    )
                case client.Unavailable():
                    return protocol.Response(503, _UNAVAILABLE)
                case client.Unreadable():
                    return protocol.Response(503, _UNAVAILABLE)
                case _ as never:
                    typing.assert_never(never)
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
        return protocol.Response(200, {"status": "deactivated"})
