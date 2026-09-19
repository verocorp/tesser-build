from __future__ import annotations  # tesser:debt TB067

import typing

import tesser.application as ts


class UserTurnMessage(ts.Port, typing.Protocol):  # tesser:debt TB051 TB052
    @property
    def text_content(self) -> str | None: ...


class UserTurnCompletedRequest(ts.Request):  # tesser:debt TB052
    def __init__(self, call_id: str, message: UserTurnMessage) -> None:  # tesser:debt TB080
        self.call_id = call_id
        self.message = message


class UserTurnCompletedResponse(ts.Response):  # tesser:debt TB052
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class UserStateChangedEvent(ts.Port, typing.Protocol):  # tesser:debt TB051 TB052
    @property
    def new_state(self) -> str: ...


class UserStateChangedRequest(ts.Request):  # tesser:debt TB052
    def __init__(self, call_id: str, event: UserStateChangedEvent) -> None:  # tesser:debt TB080
        self.call_id = call_id
        self.event = event


class UserStateChangedResponse(ts.Response):  # tesser:debt TB052
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class CallEventsApplicationClient(ts.Client, typing.Protocol):  # tesser:debt TB081
    async def user_turn_completed(  # tesser:debt TB081
        self, user_turn_completed_request: UserTurnCompletedRequest
    ) -> UserTurnCompletedResponse: ...

    async def user_state_changed(  # tesser:debt TB081
        self, user_state_changed_request: UserStateChangedRequest
    ) -> UserStateChangedResponse: ...
