from __future__ import annotations

import typing

import tesser.context as ts


class PlaceCallRequest(ts.Request):

    def __init__(self) -> None:
        return None


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


class PersonJoinedRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonJoinedResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class PersonTurnCompletedRequest(ts.Request):

    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class PersonTurnCompletedResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AttendCallRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class AttendCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class SpeakUtteranceRequest(ts.Request):

    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class SpeakUtteranceResponse(ts.Response):

    def __init__(self, call_id: str, text: str) -> None:
        self.call_id = call_id
        self.text = text


class CallNotFound(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[tuple[type[CallNotFound]]] = (CallNotFound,)


class CallsClient(ts.Client, typing.Protocol):

    async def place_call(self, place_call_request: PlaceCallRequest) -> PlaceCallResponse: ...

    async def get_call(self, get_call_request: GetCallRequest) -> GetCallResponse: ...

    async def person_joined(self, person_joined_request: PersonJoinedRequest) -> PersonJoinedResponse: ...

    async def person_turn_completed(
        self, person_turn_completed_request: PersonTurnCompletedRequest
    ) -> PersonTurnCompletedResponse: ...

    async def attend_call(self, attend_call_request: AttendCallRequest) -> AttendCallResponse: ...

    async def speak_utterance(self, speak_utterance_request: SpeakUtteranceRequest) -> SpeakUtteranceResponse: ...
