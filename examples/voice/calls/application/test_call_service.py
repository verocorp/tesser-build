from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client


@ts.fake
class FakeConductCallRelay(relays.ConductCallRelay):

    def __init__(self) -> None:
        self.conducted: list[relays.ConductCallRequest] = []

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request)
        return relays.ConductCallResponse(call_id=str(conduct_call_request.call.identity))


@ts.fake
class FakePersonAnsweredRelay(relays.PersonAnsweredRelay):

    def __init__(self) -> None:
        self.answered: list[relays.PersonAnsweredRequest] = []

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self.answered.append(person_answered_request)
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)


@ts.fake
class FakePersonUtteranceRelay(relays.PersonUtteranceRelay):

    def __init__(self) -> None:
        self.uttered: list[relays.PersonUtteranceRequest] = []

    async def run_person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        self.uttered.append(person_utterance_request)
        return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def issue_call_id(self, issue_call_id_request: ports.IssueCallIdRequest) -> ports.IssueCallIdResponse:
        return ports.IssueCallIdResponse(call_id="issued-1")

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id,
            person_name=save_call_request.person_name,
            phone_number=save_call_request.phone_number,
        )
        return ports.SaveCallResponse(call_id=save_call_request.call_id)

    async def load_call(self, load_call_request: ports.LoadCallRequest) -> ports.LoadCallResponse:
        if load_call_request.call_id not in self._calls:
            return ports.LoadCallResponse(outcome=ports.LoadCallOutcome.NOT_FOUND, calls=())
        return ports.LoadCallResponse(
            outcome=ports.LoadCallOutcome.FOUND, calls=(self._calls[load_call_request.call_id],)
        )


@ts.fake
class FakeCallStore(ports.CallStore):

    def __init__(self) -> None:
        self.calls: dict[str, ports.Call] = {}

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.CallRepository]:
        yield FakeCallRepository(self.calls)


@ts.helper
def place_call_request(person_name: str = "Ada", phone_number: str = "+15555550100") -> client.PlaceCallRequest:
    return client.PlaceCallRequest(person_name=person_name, phone_number=phone_number)


class TestCallService:

    async def test_placing_a_call_conducts_it_for_the_person_it_was_placed_for(self) -> None:
        fake_conduct_call_relay = FakeConductCallRelay()
        call_service = application.CallService(
            fake_conduct_call_relay, FakePersonAnsweredRelay(), FakePersonUtteranceRelay(), FakeCallStore()
        )

        place_call_response = await call_service.place_call(place_call_request(person_name="Grace"))

        assert [
            (str(conducted.call.identity), str(conducted.call.person.name))
            for conducted in fake_conduct_call_relay.conducted
        ] == [(place_call_response.call_id, "Grace")]

    async def test_a_placed_call_starts_by_asking_for_the_name(self) -> None:
        fake_conduct_call_relay = FakeConductCallRelay()
        call_service = application.CallService(
            fake_conduct_call_relay, FakePersonAnsweredRelay(), FakePersonUtteranceRelay(), FakeCallStore()
        )

        await call_service.place_call(place_call_request())

        assert [str(conducted.call.step) for conducted in fake_conduct_call_relay.conducted] == ["ask_name"]

    async def test_a_placed_call_takes_the_call_id_the_store_issued(self) -> None:
        call_service = application.CallService(
            FakeConductCallRelay(), FakePersonAnsweredRelay(), FakePersonUtteranceRelay(), FakeCallStore()
        )

        place_call_response = await call_service.place_call(place_call_request())

        assert place_call_response.call_id == "issued-1"

    async def test_a_saved_call_is_read_back_by_its_call_id(self) -> None:
        fake_call_store = FakeCallStore()
        fake_call_store.calls["c1"] = ports.Call(call_id="c1", person_name="Grace", phone_number="+15555550100")
        call_service = application.CallService(
            FakeConductCallRelay(), FakePersonAnsweredRelay(), FakePersonUtteranceRelay(), fake_call_store
        )

        get_call_response = await call_service.get_call(client.GetCallRequest(call_id="c1"))

        assert get_call_response.call.person_name == "Grace"

    async def test_a_call_that_was_never_placed_is_not_found(self) -> None:
        call_service = application.CallService(
            FakeConductCallRelay(), FakePersonAnsweredRelay(), FakePersonUtteranceRelay(), FakeCallStore()
        )

        with pytest.raises(client.CallNotFound) as raised:
            await call_service.get_call(client.GetCallRequest(call_id="never-placed"))

        assert str(raised.value) == "no call 'never-placed'"

    async def test_reporting_that_the_person_answered_signals_the_call_by_its_id(self) -> None:
        fake_person_answered_relay = FakePersonAnsweredRelay()
        call_service = application.CallService(
            FakeConductCallRelay(), fake_person_answered_relay, FakePersonUtteranceRelay(), FakeCallStore()
        )

        await call_service.report_person_answered(client.ReportPersonAnsweredRequest(call_id="c7"))

        assert [answered.call_id for answered in fake_person_answered_relay.answered] == ["c7"]

    async def test_reporting_what_the_person_said_signals_the_call_with_their_words(self) -> None:
        fake_person_utterance_relay = FakePersonUtteranceRelay()
        call_service = application.CallService(
            FakeConductCallRelay(), FakePersonAnsweredRelay(), fake_person_utterance_relay, FakeCallStore()
        )

        await call_service.report_person_utterance(
            client.ReportPersonUtteranceRequest(call_id="c7", text="my name is Grace")
        )

        assert [(uttered.call_id, uttered.text) for uttered in fake_person_utterance_relay.uttered] == [
            ("c7", "my name is Grace")
        ]

    async def test_reporting_a_blank_utterance_signals_nothing(self) -> None:
        fake_person_utterance_relay = FakePersonUtteranceRelay()
        call_service = application.CallService(
            FakeConductCallRelay(), FakePersonAnsweredRelay(), fake_person_utterance_relay, FakeCallStore()
        )

        await call_service.report_person_utterance(client.ReportPersonUtteranceRequest(call_id="c7", text="   "))

        assert fake_person_utterance_relay.uttered == []
