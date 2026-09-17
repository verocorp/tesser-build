from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays
import calls.client as client


class MapToPersonAnsweredRequest(ts.Mapper, relays.PersonAnsweredRequest):

    def __init__(self, report_person_answered_request: client.ReportPersonAnsweredRequest) -> None:
        super().__init__(call_id=report_person_answered_request.call_id)


class MapToReportPersonAnsweredResponse(ts.Mapper, client.ReportPersonAnsweredResponse):

    def __init__(self, person_answered_response: relays.PersonAnsweredResponse) -> None:
        super().__init__(call_id=person_answered_response.call_id)


class MapToPersonUtteranceRequest(ts.Mapper, relays.PersonUtteranceRequest):

    def __init__(self, report_person_utterance_request: client.ReportPersonUtteranceRequest) -> None:
        super().__init__(
            call_id=report_person_utterance_request.call_id, text=report_person_utterance_request.text
        )


class MapToReportPersonUtteranceResponse(ts.Mapper, client.ReportPersonUtteranceResponse):

    def __init__(self, person_utterance_response: relays.PersonUtteranceResponse) -> None:
        super().__init__(call_id=person_utterance_response.call_id)


class CallEventsService(ts.ApplicationService):

    def __init__(self, call_events_relay: relays.CallEventsRelay) -> None:
        self._call_events_relay = call_events_relay

    async def report_person_answered(
        self, report_person_answered_request: client.ReportPersonAnsweredRequest
    ) -> client.ReportPersonAnsweredResponse:
        person_answered_response = await self._call_events_relay.run_person_answered(
            MapToPersonAnsweredRequest(report_person_answered_request)
        )
        return MapToReportPersonAnsweredResponse(person_answered_response)

    async def report_person_utterance(
        self, report_person_utterance_request: client.ReportPersonUtteranceRequest
    ) -> client.ReportPersonUtteranceResponse:
        person_utterance_response = await self._call_events_relay.run_person_utterance(
            MapToPersonUtteranceRequest(report_person_utterance_request)
        )
        return MapToReportPersonUtteranceResponse(person_utterance_response)
