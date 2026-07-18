"""Inbound HTTP handler for the campaign context (transport layer 1): translate
wire (JSON) <-> the public ``Client`` DTOs, one ``Client`` call per endpoint, and
map errors to a status. The wire/JSON shape is NOT the context's contract — it is
translated to/from ``Client`` DTOs here, so a JSON change never reaches the domain.

Error mapping goes through the pure ``errors.status_for``; an ``InfraError`` (e.g.
a linkpolicy outage that failed the vetting call) becomes 503, which is how the
fail-closed cross-context call surfaces to the client.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from campaign.client import Client, CreateLinkRequest, ResolveRequest
from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]


class BadRequest(Exception):
    """A transport-level failure (unparseable/wrong-shape request) -> 400."""


@dataclass(frozen=True)
class Response:
    status: int
    body: JSONObject


class Handler:
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_link(self, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            resp = self._client.create_link(
                CreateLinkRequest(slug=_str(body.get("slug")), target_url=_str(body.get("target_url")))
            )
            return Response(201, {"slug": resp.slug, "target_url": resp.target_url})

        return self._respond(run)

    def resolve(self, slug: str) -> Response:
        def run() -> Response:
            resp = self._client.resolve(ResolveRequest(slug=slug))
            return Response(302, {"location": resp.target_url})

        return self._respond(run)

    def _respond(self, run: Callable[[], Response]) -> Response:
        try:
            return run()
        except BadRequest as e:
            return Response(400, _problem("malformed_request", str(e)))
        except DomainError as e:
            return Response(status_for(e.kind), _problem(e.code, e.message))
        except InfraError:
            return Response(503, _problem("unavailable", "a dependency is unavailable; please retry"))
        except Exception:
            return Response(500, _problem("internal", "unexpected error"))


def _problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


def _parse(raw: str) -> JSONObject:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


def _str(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
