from __future__ import annotations

import json

from httpwire import HttpRequest, JSONObject, Response, decode_body


def json_request(body: JSONObject) -> HttpRequest:
    return HttpRequest(body=json.dumps(body).encode("utf-8"))


def json_body(resp: Response) -> JSONObject:
    return decode_body(resp.body)
