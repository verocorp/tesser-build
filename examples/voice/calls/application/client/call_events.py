from __future__ import annotations  # tesser:debt TB067

import typing

import tesser.application as ts


class UserInputTranscribedEvent(ts.Port, typing.Protocol):  # tesser:debt TB051 TB052

    @property
    def transcript(self) -> str: ...

    @property
    def is_final(self) -> bool: ...


class UserInputTranscribedRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, call_id: str, event: UserInputTranscribedEvent) -> None:  # tesser:debt TB080
        self.call_id = call_id
        self.event = event


class UserInputTranscribedResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class CallEventsApplicationClient(ts.Client, typing.Protocol):  # tesser:debt TB081

    async def user_input_transcribed(  # tesser:debt TB081
        self, user_input_transcribed_request: UserInputTranscribedRequest
    ) -> UserInputTranscribedResponse: ...
