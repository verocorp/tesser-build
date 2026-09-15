from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class DialingApplicationClient(ts.Client, typing.Protocol):

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse: ...

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse: ...
