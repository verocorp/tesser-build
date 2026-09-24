from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import alpha.application as application
import alpha.application.ports as ports
import alpha.application.relays as relays
import alpha.client as client


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[str] = []
        self.standing_by_name: dict[str, str] = {}

    async def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        self.saved.append(save_widget_request.name)
        self.standing_by_name[save_widget_request.name] = save_widget_request.standing
        return ports.SaveWidgetResponse(name=save_widget_request.name)

    async def find_widget(self, find_widget_request: ports.FindWidgetRequest) -> ports.FindWidgetResponse:
        return ports.FindWidgetResponse(outcome=ports.FindWidgetOutcome.YES)


@ts.fake
class FakeWidgetStore(ports.WidgetStore):

    def __init__(self, fake_widget_repository: FakeWidgetRepository) -> None:
        self._fake_widget_repository = fake_widget_repository

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.WidgetRepository]:
        yield self._fake_widget_repository


@ts.fake
class FakeOkBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        self.checked.append(check_name_request.name)
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.OK)


@ts.fake
class FakeRefusedBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        self.checked.append(check_name_request.name)
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.REFUSED)


@ts.fake
class FakeWidgetOrchestratorRelay(relays.WidgetOrchestratorRelay):

    def __init__(self) -> None:
        self.registered: list[str] = []
        self.approved: list[str] = []

    async def start_register_widget(
        self, register_widget_request: relays.RegisterWidgetRequest
    ) -> relays.StartRegisterWidgetResponse:
        self.registered.append(str(register_widget_request.name))
        return relays.StartRegisterWidgetResponse(name=str(register_widget_request.name))

    async def run_approve_widget(self, approve_widget_request: relays.ApproveWidgetRequest) -> relays.ApproveWidgetResponse:
        self.approved.append(approve_widget_request.name)
        return relays.ApproveWidgetResponse(name=approve_widget_request.name)


@ts.helper
def add_part_request(name: str = "a", part: str = "p") -> client.AddPartRequest:
    return client.AddPartRequest(name=name, part=part)


class TestAlphaService:

    async def test_add_answers_the_added_name(self) -> None:
        alpha_service = application.AlphaService(FakeWidgetStore(FakeWidgetRepository()), FakeOkBetaCheck(), FakeWidgetOrchestratorRelay())
        add_part_response = await alpha_service.add_part(add_part_request())
        assert add_part_response.name == "a"

    async def test_a_new_part_is_taken_and_the_widget_saved_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = await application.AlphaService(FakeWidgetStore(fake_widget_repository), fake_ok_beta_check, FakeWidgetOrchestratorRelay()).add_part(add_part_request(name="a", part="p"))
        assert fake_ok_beta_check.checked == []
        assert add_part_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    async def test_a_held_part_cleared_by_beta_is_persisted_as_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = await application.AlphaService(FakeWidgetStore(fake_widget_repository), fake_ok_beta_check, FakeWidgetOrchestratorRelay()).add_part(add_part_request(name="a", part="a"))
        assert fake_ok_beta_check.checked == ["a"]
        assert add_part_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    async def test_a_held_part_refused_by_beta_is_persisted_as_released(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_refused_beta_check = FakeRefusedBetaCheck()
        add_part_response = await application.AlphaService(FakeWidgetStore(fake_widget_repository), fake_refused_beta_check, FakeWidgetOrchestratorRelay()).add_part(add_part_request(name="a", part="a"))
        assert fake_refused_beta_check.checked == ["a"]
        assert add_part_response.standing == "released"
        assert fake_widget_repository.standing_by_name == {"a": "released"}

    async def test_an_empty_name_is_rejected_in_the_context_s_own_words(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(FakeWidgetStore(fake_widget_repository), FakeOkBetaCheck(), FakeWidgetOrchestratorRelay())
        with pytest.raises(client.WidgetRejected) as raised:
            await alpha_service.add_part(add_part_request(name=""))
        assert raised.value.code == "empty_name"
        assert fake_widget_repository.saved == []

    async def test_an_empty_part_is_rejected_before_the_widget_is_saved(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(FakeWidgetStore(fake_widget_repository), FakeOkBetaCheck(), FakeWidgetOrchestratorRelay())
        with pytest.raises(client.WidgetRejected) as raised:
            await alpha_service.add_part(add_part_request(part=""))
        assert raised.value.code == "empty_identity"
        assert fake_widget_repository.saved == []

    async def test_approve_then_create_each_reach_the_widget_s_orchestrator_once(self) -> None:
        fake_widget_orchestrator_relay = FakeWidgetOrchestratorRelay()
        alpha_service = application.AlphaService(FakeWidgetStore(FakeWidgetRepository()), FakeOkBetaCheck(), fake_widget_orchestrator_relay)
        approve_widget_response = await alpha_service.approve_widget(client.ApproveWidgetRequest(name="a"))
        create_widget_response = await alpha_service.create_widget(client.CreateWidgetRequest(name="a"))
        assert (approve_widget_response.name, create_widget_response.name) == ("a", "a")
        assert (fake_widget_orchestrator_relay.approved, fake_widget_orchestrator_relay.registered) == (["a"], ["a"])
