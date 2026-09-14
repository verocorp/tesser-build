from __future__ import annotations

import contextlib
import typing

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.client as client


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id,
            person_name=save_call_request.person_name,
            phone_number=save_call_request.phone_number,
        )
        return ports.SaveCallResponse(call_id=save_call_request.call_id)

    async def load_call(self, load_call_request: ports.LoadCallRequest) -> ports.LoadCallResponse:
        return ports.LoadCallResponse(calls=(self._calls[load_call_request.call_id],))


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


class TestCallsService:

    async def test_a_placed_call_is_saved_under_the_call_id_it_answers(self) -> None:
        fake_call_store = FakeCallStore()
        calls_service = application.CallsService(fake_call_store)

        place_call_response = await calls_service.place_call(place_call_request(person_name="Grace"))

        assert fake_call_store.calls[place_call_response.call_id].person_name == "Grace"

    async def test_a_saved_call_is_read_back_by_its_call_id(self) -> None:
        fake_call_store = FakeCallStore()
        fake_call_store.calls["c1"] = ports.Call(call_id="c1", person_name="Grace", phone_number="+15555550100")
        calls_service = application.CallsService(fake_call_store)

        get_call_response = await calls_service.get_call(client.GetCallRequest(call_id="c1"))

        assert get_call_response.call.person_name == "Grace"
