from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

import tesser.srv as ts

from protocol.http import Endpoint


@dataclass(frozen=True)
class Route:  # tessercheck:ignore TB052
    method: str
    pattern: str
    endpoint: Endpoint


@dataclass(frozen=True)
class Match:  # tessercheck:ignore TB052
    endpoint: Endpoint
    path_params: dict[str, str]
    query_params: dict[str, str]


@ts.function
def split(raw_path: str) -> tuple[str, dict[str, str]]:
    parts = urllib.parse.urlsplit(raw_path)
    query = {name: values[-1] for name, values in urllib.parse.parse_qs(parts.query).items()}
    return parts.path, query


@ts.function
def match(routes: tuple[Route, ...], method: str, raw_path: str) -> Match | None:
    path, query_params = split(raw_path)
    for route in routes:
        if route.method != method:
            continue
        path_params = _path_params(route.pattern, path)
        if path_params is None:
            continue
        return Match(route.endpoint, path_params, query_params)
    return None


@ts.function
def _path_params(pattern: str, path: str) -> dict[str, str] | None:
    expected = pattern.strip("/").split("/")
    actual = path.strip("/").split("/")
    if len(expected) != len(actual):
        return None
    params: dict[str, str] = {}
    for want, got in zip(expected, actual, strict=True):
        if want.startswith("{") and want.endswith("}"):
            if not got:
                return None
            params[want[1:-1]] = urllib.parse.unquote(got)
            continue
        if want != got:
            return None
    return params
