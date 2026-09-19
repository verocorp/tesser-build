from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class CallEventsApplicationClient(ts.Client, typing.Protocol):  # tesser:debt TB081

    async def person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse: ...
