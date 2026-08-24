from __future__ import annotations

import json
import urllib.parse
import collections.abc as abc
import typing

import tesser.srv as ts


JSONObject = dict[str, object]  # tesser:debt TB051


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
        path_params: abc.Mapping[str, str],
        query_params: abc.Mapping[str, str],
        headers: abc.Mapping[str, str],
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
    path_params: abc.Mapping[str, str]
    query_params: abc.Mapping[str, str]
    headers: abc.Mapping[str, str]
    body: bytes

    def json_body(self) -> JSONObject:
        raw = self.body
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise BadRequest(f"malformed JSON: {e}") from e
        if not isinstance(data, dict):
            raise BadRequest("expected a JSON object")
        return data

    def path_param(self, name: str) -> str:
        value = self.path_params.get(name)
        if not value:
            raise BadRequest(f"missing path parameter: {name}")
        return value


class HttpResponse(ts.Response):

    def __init__(self, status_code: int, body: bytes, headers: abc.Mapping[str, str]) -> None:
        super().__init__(
            status_code=status_code,
            body=body,
            headers=dict(headers),
        )

    status_code: int
    body: bytes
    headers: abc.Mapping[str, str]

    @classmethod
    def json(cls, status_code: int, body: JSONObject, headers: abc.Mapping[str, str] | None = None) -> HttpResponse:
        payload = json.dumps(body).encode("utf-8")
        declared = dict(headers or {})
        if not any(name.lower() == "content-type" for name in declared):
            declared["Content-Type"] = "application/json"
        return cls(status_code, payload, declared)

    @classmethod
    def problem(cls, status_code: int, code: str, detail: str) -> HttpResponse:
        return cls.json(status_code, {"type": f"/problems/{code}", "detail": detail})  # tesser:debt TB051

    @classmethod
    def redirect(cls, url: str, status_code: int = 302) -> HttpResponse:
        if any(char in url for char in "\r\n\x00"):
            raise BadRequest("a redirect target carries a control character")
        return cls(status_code, b"", {"Location": url})

    def json_body(self) -> JSONObject:
        raw = self.body
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise BadRequest(f"malformed JSON: {e}") from e
        if not isinstance(data, dict):
            raise BadRequest("expected a JSON object")
        return data


class Endpoint(ts.Port, typing.Protocol):

    def __call__(self, request: HttpRequest, /) -> HttpResponse: ...


class Route(ts.Record):

    def __init__(self, method: str, pattern: str, endpoint: Endpoint) -> None:
        super().__init__(method=method, pattern=pattern, endpoint=endpoint)

    method: str
    pattern: str
    endpoint: Endpoint


class Match(ts.Record):

    def __init__(
        self,
        endpoint: Endpoint,
        path_params: abc.Mapping[str, str],
        query_params: abc.Mapping[str, str],
    ) -> None:
        super().__init__(
            endpoint=endpoint,
            path_params=dict(path_params),
            query_params=dict(query_params),
        )

    endpoint: Endpoint
    path_params: abc.Mapping[str, str]
    query_params: abc.Mapping[str, str]


class Router(ts.Record):

    def __init__(self, routes: tuple[Route, ...]) -> None:
        super().__init__(routes=routes)

    routes: tuple[Route, ...]

    def match(self, method: str, raw_path: str) -> Match | None:
        parts = urllib.parse.urlsplit(raw_path)
        query_params = {
            name: values[-1]
            for name, values in urllib.parse.parse_qs(parts.query).items()
        }
        for route in self.routes:
            if route.method != method:
                continue
            expected = route.pattern.strip("/").split("/")
            actual = parts.path.strip("/").split("/")
            if len(expected) != len(actual):
                continue
            params: dict[str, str] = {}
            matched = True
            for want, got in zip(expected, actual, strict=True):
                if want.startswith("{") and want.endswith("}"):
                    if not got:
                        matched = False
                        break
                    params[want[1:-1]] = urllib.parse.unquote(got)
                    continue
                if want != got:
                    matched = False
                    break
            if not matched:
                continue
            return Match(route.endpoint, params, query_params)
        return None
