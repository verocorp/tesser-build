from __future__ import annotations

import tesser.srv as ts


class BadRequest(ts.Rejection):
    pass


class Response(ts.Response):

    def __init__(self, status: int, body: dict[str, object]) -> None:
        super().__init__(status=status, body=body)

    status: int
    body: dict[str, object]

