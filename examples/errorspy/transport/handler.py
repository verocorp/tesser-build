from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

import errors
from app.service import CampaignService
from domain.campaign import CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import DateWindowSpec, Slug, TargetURL
from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]


class BadRequest(Exception):
    pass


@dataclass(frozen=True)
class Response:
    status: int
    body: JSONObject


class Handler:
    def __init__(self, service: CampaignService) -> None:
        self._service = service

    def create_campaign(self, campaign_id: str, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            window = _obj(body.get("window"), "window")
            links = _arr(body.get("links"), "links")
            spec = CampaignSpec(
                window=DateWindowSpec(
                    start=_str(window.get("start")), end=_str(window.get("end"))
                ),
                links=tuple(
                    ShortLinkSpec(
                        slug=_str(_obj(link, "link").get("slug")),
                        target_url=_str(_obj(link, "link").get("target_url")),
                    )
                    for link in links
                ),
            )
            self._service.create(campaign_id, spec)
            return Response(201, {"id": campaign_id})

        return self._respond(run)

    def get_campaign(self, campaign_id: str) -> Response:
        def run() -> Response:
            campaign = self._service.get(campaign_id)
            return Response(
                200,
                {
                    "id": campaign.id,
                    "links": [str(link.slug) for link in campaign.links],
                },
            )

        return self._respond(run)

    def add_link(self, campaign_id: str, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            slug = _str(body.get("slug"))
            target_url = _str(body.get("target_url"))
            errors.collect(
                slug=lambda: Slug(slug), target_url=lambda: TargetURL(target_url)
            )
            self._service.add_link(
                campaign_id, ShortLinkSpec(slug=slug, target_url=target_url)
            )
            return Response(200, {"status": "added"})

        return self._respond(run)

    def deactivate_link(self, campaign_id: str, slug: str) -> Response:
        def run() -> Response:
            self._service.deactivate_link(campaign_id, slug)
            return Response(200, {"status": "deactivated"})

        return self._respond(run)

    def _respond(self, run: Callable[[], Response]) -> Response:
        try:
            return run()
        except BadRequest as e:
            return Response(400, _problem("malformed_request", "Bad Request", 400, str(e)))
        except DomainError as e:
            status = status_for(e.kind)
            return Response(status, _problem_for(e, status))
        except InfraError:
            return Response(
                503, _problem("unavailable", "Service Unavailable", 503, "please retry")
            )
        except Exception:  # noqa: BLE001 — the unexpected-500 backstop
            return Response(
                500, _problem("internal", "Internal Server Error", 500, "unexpected error")
            )


def _problem(code: str, title: str, status: int, detail: str) -> JSONObject:
    return {
        "type": f"/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
    }


def _problem_for(err: DomainError, status: int) -> JSONObject:
    body = _problem(err.code, err.code.replace("_", " "), status, err.message)
    if err.field is not None:
        body["field"] = err.field
    if err.problems:
        body["invalid-params"] = [
            {"name": p.field, "code": p.code, "reason": p.message}
            for p in err.problems
        ]
    return body


def _parse(raw: str) -> JSONObject:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


def _obj(value: object, name: str) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest(f"{name!r} must be an object")
    return value


def _arr(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise BadRequest(f"{name!r} must be an array")
    return value


def _str(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
