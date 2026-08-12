from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Protocol

import tesser.srv as ts

JSONObject = dict[str, object]  # tessercheck:ignore TB051


class BadRequest(ts.Rejection):
    pass


class PayloadTooLarge(ts.Rejection):
    pass


class StreamingUnsupported(ts.Rejection):
    pass


class HttpRequest(ts.Request):

    def __init__(
        self,
        method: str,
        path: str,
        path_params: Mapping[str, str],
        query_params: Mapping[str, str],
        headers: Mapping[str, str],
        body: bytes,
    ) -> None:
        super().__init__(
            method=method,
            path=path,
            path_params=dict(path_params),
            query_params=dict(query_params),
            headers=dict(headers),
            body=body,
        )

    method: str
    path: str
    path_params: Mapping[str, str]
    query_params: Mapping[str, str]
    headers: Mapping[str, str]
    body: bytes

    def json_body(self) -> JSONObject:
        return _json_object(self.body)

    def path_param(self, name: str) -> str:
        value = self.path_params.get(name)
        if not value:
            raise BadRequest(f"missing path parameter: {name}")
        return value


class HttpResponse(ts.Response):

    def __init__(self, status_code: int, body: bytes, headers: Mapping[str, str]) -> None:
        super().__init__(
            status_code=status_code,
            body=body,
            headers=dict(headers),
        )

    status_code: int
    body: bytes
    headers: Mapping[str, str]

    @classmethod
    def json(cls, status_code: int, body: JSONObject, headers: Mapping[str, str] | None = None) -> HttpResponse:
        payload = json.dumps(body).encode("utf-8")
        declared = dict(headers or {})
        if not any(name.lower() == "content-type" for name in declared):
            declared["Content-Type"] = "application/json"
        return cls(status_code, payload, declared)

    @classmethod
    def problem(cls, status_code: int, code: str, detail: str) -> HttpResponse:
        return cls.json(status_code, {"type": f"/problems/{code}", "detail": detail})

    @classmethod
    def redirect(cls, url: str, status_code: int = 302) -> HttpResponse:
        if any(char in url for char in "\r\n\x00"):
            raise BadRequest("a redirect target carries a control character")
        return cls(status_code, b"", {"Location": url})

    def json_body(self) -> JSONObject:
        return _json_object(self.body)


class Endpoint(ts.Port, Protocol):

    def __call__(self, request: HttpRequest, /) -> HttpResponse: ...


@ts.function
def _json_object(raw: bytes) -> JSONObject:
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
def object_field(value: object) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest("expected a JSON object field")
    return value


@ts.function
def string_field(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
