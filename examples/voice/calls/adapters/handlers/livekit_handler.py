from __future__ import annotations

import tesser.adapters as ts

import calls.client as client
import protocol


class LivekitHandler(ts.Handler):

    def __init__(self, calls_client: client.CallsClient) -> None:
        self._calls_client = calls_client

    async def person_answered(self, person_answered: protocol.PersonAnswered) -> None:
        await self._calls_client.report_person_answered(
            client.ReportPersonAnsweredRequest(call_id=person_answered.call_id)
        )

    async def person_utterance(self, person_utterance: protocol.PersonUtterance) -> None:
        await self._calls_client.report_person_utterance(
            client.ReportPersonUtteranceRequest(call_id=person_utterance.call_id, text=person_utterance.text)
        )
