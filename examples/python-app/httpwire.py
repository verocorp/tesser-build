from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]

MAX_BUFFERED_BODY = 1_048_576


class BadRequest(Exception):
    pass


class PayloadTooLarge(Exception):
    pass


class StreamingUnsupported(Exception):
    pass


@dataclass(frozen=True)
class HttpRequest:
    method: str = "GET"
    path: str = "/"
    path_params: Mapping[str, str] = field(default_factory=dict)
    query_params: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass(frozen=True)
class Response:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


Endpoint = Callable[[HttpRequest], Response]


def problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


def json_response(status_code: int, body: JSONObject, headers: Mapping[str, str] | None = None) -> Response:
    payload = json.dumps(body).encode("utf-8")
    return Response(status_code, payload, {"Content-Type": "application/json", **(headers or {})})


def redirect(url: str, status_code: int = 302) -> Response:
    return Response(status_code, b"", {"Location": url})


def respond(run: Callable[[], Response]) -> Response:
    try:
        return run()
    except BadRequest as e:
        return json_response(400, problem("malformed_request", str(e)))
    except PayloadTooLarge as e:
        return json_response(413, problem("payload_too_large", str(e)))
    except StreamingUnsupported as e:
        return json_response(411, problem("length_required", str(e)))
    except DomainError as e:
        return json_response(status_for(e.kind), problem(e.code, e.message))
    except InfraError:
        return json_response(503, problem("unavailable", "a dependency is unavailable; please retry"))
    except Exception:
        return json_response(500, problem("internal", "unexpected error"))


def content_length(headers: Mapping[str, str]) -> int:
    lowered = {name.lower(): value for name, value in headers.items()}
    if "chunked" in lowered.get("transfer-encoding", "").lower():
        raise StreamingUnsupported(
            "this host buffers; declare a Content-Length (streaming bodies are a documented boundary)"
        )
    raw = lowered.get("content-length") or "0"
    try:
        declared = int(raw)
    except ValueError as e:
        raise BadRequest(f"invalid Content-Length: {raw!r}") from e
    if declared < 0:
        raise BadRequest("negative Content-Length")
    if declared > MAX_BUFFERED_BODY:
        raise PayloadTooLarge(f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit")
    return declared


def decode_body(raw: bytes) -> JSONObject:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
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
