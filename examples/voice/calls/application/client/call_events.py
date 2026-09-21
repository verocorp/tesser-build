from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class CallEventsApplicationClient(ts.Client, typing.Protocol):  # tesser:debt TB081
    async def person_joined(
        self, person_joined_request: relays.PersonJoinedRequest
    ) -> relays.PersonJoinedResponse: ...

    async def person_turn_completed(
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse: ...
