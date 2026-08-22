from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

import tesser.srv as ts

from protocol.http import Endpoint


@dataclass(frozen=True)
class Route:  # tesser:debt TB052
    method: str
    pattern: str
    endpoint: Endpoint


@dataclass(frozen=True)
class Match:  # tesser:debt TB052
    endpoint: Endpoint
    path_params: dict[str, str]
    query_params: dict[str, str]


@ts.do_not_use_function
def match(routes: tuple[Route, ...], method: str, raw_path: str) -> Match | None:  # tesser:debt TB051
    parts = urllib.parse.urlsplit(raw_path)
    query_params = {name: values[-1] for name, values in urllib.parse.parse_qs(parts.query).items()}
    for route in routes:
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
