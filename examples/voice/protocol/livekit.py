from __future__ import annotations

import tesser.srv as ts


class PersonAnswered(ts.Request):

    def __init__(self, call_id: str) -> None:
        super().__init__(call_id=call_id)

    call_id: str


class PersonUtterance(ts.Request):

    def __init__(self, call_id: str, text: str) -> None:
        super().__init__(call_id=call_id, text=text)

    call_id: str
    text: str
