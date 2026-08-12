from __future__ import annotations

import json

import tesser.srv as ts

JSONObject = dict[str, object]  # tessercheck:ignore TB051


class BadRequest(ts.Rejection):
    pass


class Response(ts.Response):

    def __init__(self, status: int, body: JSONObject) -> None:
        super().__init__(status=status, body=body)

    status: int
    body: JSONObject


@ts.function
def json_object(raw: str) -> JSONObject:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


@ts.function
def object_field(value: object, name: str) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest(f"{name!r} must be an object")
    return value


@ts.function
def array_field(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise BadRequest(f"{name!r} must be an array")
    return value


@ts.function
def string_field(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
