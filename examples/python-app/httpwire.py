from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]


class BadRequest(Exception):
    pass


@dataclass(frozen=True)
class HttpRequest:
    method: str = "GET"
    path: str = "/"
    path_params: Mapping[str, str] = field(default_factory=dict)
    query_params: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    body: JSONObject = field(default_factory=dict)


@dataclass(frozen=True)
class Response:
    status_code: int
    body: JSONObject
    headers: Mapping[str, str] = field(default_factory=dict)


Endpoint = Callable[[HttpRequest], Response]


def problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


def redirect(url: str, status_code: int = 302) -> Response:
    return Response(status_code, {}, {"Location": url})


def respond(run: Callable[[], Response]) -> Response:
    try:
        return run()
    except BadRequest as e:
        return Response(400, problem("malformed_request", str(e)))
    except DomainError as e:
        return Response(status_for(e.kind), problem(e.code, e.message))
    except InfraError:
        return Response(503, problem("unavailable", "a dependency is unavailable; please retry"))
    except Exception:
        return Response(500, problem("internal", "unexpected error"))


def decode_body(raw: str) -> JSONObject:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


def path_param(req: HttpRequest, name: str) -> str:
    value = req.path_params.get(name)
    if not value:
        raise BadRequest(f"missing path parameter: {name}")
    return value


def object_field(value: object) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest("expected a JSON object field")
    return value


def string_field(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
