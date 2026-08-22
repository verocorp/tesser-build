from __future__ import annotations

import json

import tesser.srv as ts

JSONObject = dict[str, object]  # tesser:debt TB051


class BadRequest(ts.Rejection):
    pass


class Response(ts.Response):

    def __init__(self, status: int, body: JSONObject) -> None:
        super().__init__(status=status, body=body)

    status: int
    body: JSONObject


@ts.do_not_use_function
def json_object(raw: str) -> JSONObject:  # tesser:debt TB051
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


@ts.do_not_use_function
def object_field(value: object, name: str) -> JSONObject:  # tesser:debt TB051
    if not isinstance(value, dict):
        raise BadRequest(f"{name!r} must be an object")
    return value


@ts.do_not_use_function
def array_field(value: object, name: str) -> list[object]:  # tesser:debt TB051
    if not isinstance(value, list):
        raise BadRequest(f"{name!r} must be an array")
    return value


@ts.do_not_use_function
def string_field(value: object) -> str:  # tesser:debt TB051
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
