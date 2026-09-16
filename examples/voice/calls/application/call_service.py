from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client
import calls.domain as domain


class MapToCallSpec(ts.Mapper, domain.CallSpec):

    def __init__(
        self,
        place_call_request: client.PlaceCallRequest,
        issue_call_id_response: ports.IssueCallIdResponse,
    ) -> None:
        super().__init__(
            call_id=issue_call_id_response.call_id,
            person=domain.PersonSpec(
                name=place_call_request.person_name,
                phone_number=place_call_request.phone_number,
            ),
            turns=(),
            step=domain.ASK_NAME,
        )


class MapToConductCallRequest(ts.Mapper, relays.ConductCallRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToPlaceCallResponse(ts.Mapper, client.PlaceCallResponse):

    def __init__(self, conduct_call_response: relays.ConductCallResponse) -> None:
        super().__init__(call_id=conduct_call_response.call_id)


class MapToLoadCallRequest(ts.Mapper, ports.LoadCallRequest):

    def __init__(self, call_id: domain.CallId) -> None:
        super().__init__(call_id=str(call_id))


class MapToCall(ts.Mapper, client.Call):

    def __init__(self, call: ports.Call) -> None:
        super().__init__(call_id=call.call_id, person_name=call.person_name)


class MapToCallPresenceSpec(ts.Mapper, domain.CallPresenceSpec):

    def __init__(self, load_call_response: ports.LoadCallResponse) -> None:
        super().__init__(presence=load_call_response.outcome.value)


class MapToGetCallResponse(ts.Mapper, client.GetCallResponse):

    def __init__(self, call: ports.Call) -> None:
        super().__init__(call=MapToCall(call))


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


class CallService(ts.ApplicationService):

    def __init__(
        self,
        conduct_call_relay: relays.ConductCallRelay,
        person_answered_relay: relays.PersonAnsweredRelay,
        person_utterance_relay: relays.PersonUtteranceRelay,
        call_store: ports.CallStore,
    ) -> None:
        self._conduct_call_relay = conduct_call_relay
        self._person_answered_relay = person_answered_relay
        self._person_utterance_relay = person_utterance_relay
        self._call_store = call_store

    async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
        async with self._call_store.transaction() as call_repository:
            issue_call_id_response = await call_repository.issue_call_id(ports.IssueCallIdRequest())
        call = domain.Call(MapToCallSpec(place_call_request, issue_call_id_response))
        conduct_call_response = await self._conduct_call_relay.run_conduct_call(MapToConductCallRequest(call))
        return MapToPlaceCallResponse(conduct_call_response)

    async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
        call_id = domain.CallId(get_call_request.call_id)
        async with self._call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(MapToLoadCallRequest(call_id))
        match domain.CallPresence(MapToCallPresenceSpec(load_call_response)).decide():
            case domain.CallLookup.FOUND:
                return MapToGetCallResponse(load_call_response.calls[0])
            case domain.CallLookup.NOT_FOUND:
                raise client.CallNotFound(f"no call {get_call_request.call_id!r}")
            case _ as never:
                typing.assert_never(never)

    async def report_person_answered(
        self, report_person_answered_request: client.ReportPersonAnsweredRequest
    ) -> client.ReportPersonAnsweredResponse:
        person_answered_response = await self._person_answered_relay.run_person_answered(
            MapToPersonAnsweredRequest(report_person_answered_request)
        )
        return MapToReportPersonAnsweredResponse(person_answered_response)

    async def report_person_utterance(
        self, report_person_utterance_request: client.ReportPersonUtteranceRequest
    ) -> client.ReportPersonUtteranceResponse:
        person_utterance_response = await self._person_utterance_relay.run_person_utterance(
            MapToPersonUtteranceRequest(report_person_utterance_request)
        )
        return MapToReportPersonUtteranceResponse(person_utterance_response)
