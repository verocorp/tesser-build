from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[str] = []
        self.standing_by_name: dict[str, str] = {}

    def save(self, save_request: ports.SaveRequest) -> ports.SaveResponse:
        self.saved.append(save_request.name)
        self.standing_by_name[save_request.name] = save_request.standing
        return ports.SaveResponse(name=save_request.name)


@ts.fake
class FakeOkBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        self.checked.append(check_request.name)
        return ports.CheckResponse(verdict=ports.Verdict.OK)


@ts.fake
class FakeRefusedBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        self.checked.append(check_request.name)
        return ports.CheckResponse(verdict=ports.Verdict.REFUSED)


@ts.helper
def add_request(name: str = "a", part: str = "p") -> client.AddRequest:
    return client.AddRequest(name=name, part=part)


class TestAlphaService:

    def test_add_answers_the_added_name(self) -> None:
        alpha_service = application.AlphaService(FakeWidgetRepository(), FakeOkBetaCheck())
        add_response = alpha_service.add(add_request())
        assert add_response.name == "a"

    def test_a_new_part_is_taken_and_the_widget_saved_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_response = application.AlphaService(fake_widget_repository, fake_ok_beta_check).add(add_request(name="a", part="p"))
        assert fake_ok_beta_check.checked == []
        assert add_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    def test_a_held_part_cleared_by_beta_is_persisted_as_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_response = application.AlphaService(fake_widget_repository, fake_ok_beta_check).add(add_request(name="a", part="a"))
        assert fake_ok_beta_check.checked == ["a"]
        assert add_response.standing == "kept"
        assert fake_widget_repository.standing_by_name == {"a": "kept"}

    def test_a_held_part_refused_by_beta_is_persisted_as_released(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        fake_refused_beta_check = FakeRefusedBetaCheck()
        add_response = application.AlphaService(fake_widget_repository, fake_refused_beta_check).add(add_request(name="a", part="a"))
        assert fake_refused_beta_check.checked == ["a"]
        assert add_response.standing == "released"
        assert fake_widget_repository.standing_by_name == {"a": "released"}

    def test_an_empty_name_is_rejected_in_the_context_s_own_words(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(fake_widget_repository, FakeOkBetaCheck())
        with pytest.raises(client.Rejected) as raised:
            alpha_service.add(add_request(name=""))
        assert raised.value.code == "empty_name"
        assert fake_widget_repository.saved == []

    def test_an_empty_part_is_rejected_before_the_widget_is_saved(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        alpha_service = application.AlphaService(fake_widget_repository, FakeOkBetaCheck())
        with pytest.raises(client.Rejected) as raised:
            alpha_service.add(add_request(part=""))
        assert raised.value.code == "empty_identity"
        assert fake_widget_repository.saved == []
