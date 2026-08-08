from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Final, Protocol

import tesser.srv as ts

from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]

MAX_BUFFERED_BODY: Final[int] = 1_048_576


class BadRequest(Exception):
    pass


class PayloadTooLarge(Exception):
    pass


class StreamingUnsupported(Exception):
    pass


class HttpRequest(ts.Request):

    def __init__(
        self,
        method: str = "GET",
        path: str = "/",
        path_params: Mapping[str, str] | None = None,
        query_params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        body: bytes = b"",
    ) -> None:
        super().__init__(
            method=method,
            path=path,
            path_params=dict(path_params or {}),
            query_params=dict(query_params or {}),
            headers=dict(headers or {}),
            body=body,
        )

    method: str
    path: str
    path_params: Mapping[str, str]
    query_params: Mapping[str, str]
    headers: Mapping[str, str]
    body: bytes


class Response(ts.Response):

    def __init__(
        self,
        status_code: int,
        body: bytes,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            body=body,
            headers=dict(headers or {}),
        )

    status_code: int
    body: bytes
    headers: Mapping[str, str]


class Endpoint(ts.Port, Protocol):

    def __call__(self, request: HttpRequest, /) -> Response: ...


@ts.function
def problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


@ts.function
def json_response(status_code: int, body: JSONObject, headers: Mapping[str, str] | None = None) -> Response:
    payload = json.dumps(body).encode("utf-8")
    return Response(status_code, payload, {"Content-Type": "application/json", **(headers or {})})


@ts.function
def redirect(url: str, status_code: int = 302) -> Response:
    return Response(status_code, b"", {"Location": url})


@ts.function
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


@ts.function
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


@ts.function
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


@ts.function
def path_param(req: HttpRequest, name: str) -> str:
    value = req.path_params.get(name)
    if not value:
        raise BadRequest(f"missing path parameter: {name}")
    return value


@ts.function
def object_field(value: object) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest("expected a JSON object field")
    return value


@ts.function
def string_field(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
