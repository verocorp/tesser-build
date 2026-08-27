from __future__ import annotations

import json

import tesser.srv as ts


class BadInvocation(ts.Rejection):
    pass


class WorkflowRequest(ts.Request):

    def __init__(self, key: str, body: bytes) -> None:
        super().__init__(key=key, body=body)

    key: str
    body: bytes

    def text(self, name: str) -> str:
        try:
            data = json.loads(self.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise BadInvocation(f"malformed JSON: {e}") from e
        if not isinstance(data, dict):
            raise BadInvocation("expected a JSON object")
        value = data.get(name)
        if not isinstance(value, str):
            raise BadInvocation(f"{name} must be a string")
        return value

    def integer(self, name: str) -> int:
        try:
            data = json.loads(self.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise BadInvocation(f"malformed JSON: {e}") from e
        if not isinstance(data, dict):
            raise BadInvocation("expected a JSON object")
        value = data.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise BadInvocation(f"{name} must be an integer")
        return value


class WorkflowResponse(ts.Response):

    def __init__(self, body: bytes) -> None:
        super().__init__(body=body)

    body: bytes
