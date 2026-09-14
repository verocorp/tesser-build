from __future__ import annotations

import typing

import tesser.context as ts


class PlaceCallRequest(ts.Request):

    def __init__(self, person_name: str, phone_number: str) -> None:
        self.person_name = person_name
        self.phone_number = phone_number


class PlaceCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class Call(ts.Response):

    def __init__(self, call_id: str, person_name: str) -> None:
        self.call_id = call_id
        self.person_name = person_name


class GetCallRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class GetCallResponse(ts.Response):

    def __init__(self, call: Call) -> None:
        self.call = call


class CallsClient(ts.Client, typing.Protocol):

    async def place_call(self, place_call_request: PlaceCallRequest) -> PlaceCallResponse: ...

    async def get_call(self, get_call_request: GetCallRequest) -> GetCallResponse: ...
