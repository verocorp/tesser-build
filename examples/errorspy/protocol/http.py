from __future__ import annotations

import tesser.srv as ts

JSONObject = dict[str, object]  # tesser:debt TB051


class BadRequest(ts.Rejection):
    pass


class Response(ts.Response):

    def __init__(self, status: int, body: JSONObject) -> None:
        super().__init__(status=status, body=body)

    status: int
    body: JSONObject

