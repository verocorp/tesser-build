from __future__ import annotations

import contextlib
import typing

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def issue_call_id(self, issue_call_id_request: ports.IssueCallIdRequest) -> ports.IssueCallIdResponse:
        return ports.IssueCallIdResponse(call_id="issued-1")

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id, person_name=save_call_request.person_name
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
def call_spec(call_id: str = "c1", person_name: str = "Ada") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestCallActions:

    async def test_recording_a_call_saves_the_persons_name_under_its_call_id(self) -> None:
        fake_call_store = FakeCallStore()
        call_actions = application.CallActions(fake_call_store)

        await call_actions.record_call(
            relays.RecordCallRequest(call=domain.Call(call_spec(call_id="c7", person_name="Grace")))
        )

        assert fake_call_store.calls["c7"].person_name == "Grace"

    async def test_recording_a_call_answers_the_call_id_it_saved(self) -> None:
        call_actions = application.CallActions(FakeCallStore())

        record_call_response = await call_actions.record_call(
            relays.RecordCallRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert record_call_response.call_id == "c7"
