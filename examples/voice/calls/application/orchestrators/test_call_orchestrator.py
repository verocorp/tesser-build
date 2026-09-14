from __future__ import annotations

import tesser.testing as ts

import calls.application.orchestrators as orchestrators
import calls.application.relays as relays


@ts.fake
class FakeCallActionsRunner(relays.CallActionsRunner):

    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=record_call_request.call_id)


@ts.helper
def place_call_request(
    call_id: str = "c1", person_name: str = "Ada", phone_number: str = "+15555550100"
) -> relays.PlaceCallRequest:
    return relays.PlaceCallRequest(call_id=call_id, person_name=person_name, phone_number=phone_number)


class TestCallOrchestrator:

    async def test_placing_a_call_runs_the_record_call_action_with_the_call(self) -> None:
        fake_call_actions_runner = FakeCallActionsRunner()
        call_orchestrator = orchestrators.CallOrchestrator(fake_call_actions_runner)

        await call_orchestrator.place_call(place_call_request(call_id="c7", person_name="Grace"))

        assert [
            (recorded.call_id, recorded.person_name) for recorded in fake_call_actions_runner.recorded
        ] == [("c7", "Grace")]

    async def test_placing_a_call_answers_the_call_id_the_action_recorded(self) -> None:
        call_orchestrator = orchestrators.CallOrchestrator(FakeCallActionsRunner())

        place_call_response = await call_orchestrator.place_call(place_call_request(call_id="c7"))

        assert place_call_response.call_id == "c7"
