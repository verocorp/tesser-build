from __future__ import annotations

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

    def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        self.saved.append(save_widget_request.name)
        self.standing_by_name[save_widget_request.name] = save_widget_request.standing
        return ports.SaveWidgetResponse(name=save_widget_request.name)


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
class FakeRegisterWidgetRelay(relays.RegisterWidgetRelay):

    def __init__(self) -> None:
        self.registered: list[str] = []

    def run_register_widget(
        self, register_widget_request: relays.RegisterWidgetRequest
    ) -> relays.RegisterWidgetResponse:
        self.registered.append(register_widget_request.name)
        return relays.RegisterWidgetResponse(name=register_widget_request.name)


@ts.helper
def add_part_request(name: str = "a", part: str = "p") -> client.AddPartRequest:
    return client.AddPartRequest(name=name, part=part)


class TestAlphaService:

    def test_add_answers_the_added_name(self) -> None:
        alpha_service = application.AlphaService(FakeWidgetRepository(), FakeOkBetaCheck(), FakeRegisterWidgetRelay())
        add_part_response = alpha_service.add_part(add_part_request())
        assert add_part_response.name == "a"

    def test_a_new_part_is_taken_and_the_widget_saved_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = application.AlphaService(fake_widget_repository, fake_ok_beta_check, FakeRegisterWidgetRelay()).add_part(add_part_request(name="a", part="p"))
        assert fake_ok_beta_check.checked == []
        assert add_part_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    def test_a_held_part_cleared_by_beta_is_persisted_as_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = application.AlphaService(fake_widget_repository, fake_ok_beta_check, FakeRegisterWidgetRelay()).add_part(add_part_request(name="a", part="a"))
        assert fake_ok_beta_check.checked == ["a"]
        assert add_part_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    def test_a_held_part_refused_by_beta_is_persisted_as_released(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_refused_beta_check = FakeRefusedBetaCheck()
        add_part_response = application.AlphaService(fake_widget_repository, fake_refused_beta_check, FakeRegisterWidgetRelay()).add_part(add_part_request(name="a", part="a"))
        assert fake_refused_beta_check.checked == ["a"]
        assert add_part_response.standing == "released"
        assert fake_widget_repository.standing_by_name == {"a": "released"}

    def test_an_empty_name_is_rejected_in_the_context_s_own_words(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(fake_widget_repository, FakeOkBetaCheck(), FakeRegisterWidgetRelay())
        with pytest.raises(client.WidgetRejected) as raised:
            alpha_service.add_part(add_part_request(name=""))
        assert raised.value.code == "empty_name"
        assert fake_widget_repository.saved == []

    def test_an_empty_part_is_rejected_before_the_widget_is_saved(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(fake_widget_repository, FakeOkBetaCheck(), FakeRegisterWidgetRelay())
        with pytest.raises(client.WidgetRejected) as raised:
            alpha_service.add_part(add_part_request(part=""))
        assert raised.value.code == "empty_identity"
        assert fake_widget_repository.saved == []

    def test_create_registers_the_widget_through_its_relay_once_and_answers_its_name(self) -> None:
        fake_register_widget_relay = FakeRegisterWidgetRelay()
        alpha_service = application.AlphaService(FakeWidgetRepository(), FakeOkBetaCheck(), fake_register_widget_relay)
        create_widget_response = alpha_service.create_widget(client.CreateWidgetRequest(name="a"))
        assert create_widget_response.name == "a"
        assert fake_register_widget_relay.registered == ["a"]
