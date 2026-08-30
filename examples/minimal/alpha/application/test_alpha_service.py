from __future__ import annotations

import tesser.testing as ts

import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client


@ts.fake
class FakeWidgetRepository(widget_repository.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[str] = []
        self.standing_by_name: dict[str, str] = {}

    def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self.saved.append(request.name)
        self.standing_by_name[request.name] = request.standing
        return widget_repository.SaveResponse(name=request.name)


@ts.fake
class FakeOkBetaCheck(beta_check.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        self.checked.append(request.name)
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


@ts.fake
class FakeRefusedBetaCheck(beta_check.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        self.checked.append(request.name)
        return beta_check.CheckResponse(verdict=beta_check.Verdict.REFUSED)


@ts.helper
def add_request(name: str = "a", part: str = "p") -> client.AddRequest:
    return client.AddRequest(name=name, part=part)


class TestAlphaService:

    def test_add_answers_the_added_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetRepository(), FakeOkBetaCheck())
        added = service.add(add_request())
        assert added.name == "a"

    def test_a_new_part_is_taken_and_the_widget_saved_kept(self) -> None:
        widgets = FakeWidgetRepository()
        checks = FakeOkBetaCheck()
        added = alpha_service.AlphaService(widgets, checks).add(add_request(name="a", part="p"))
        assert checks.checked == []
        assert added.standing == "kept"
        assert widgets.standing_by_name == {"a": "kept"}

    def test_a_held_part_cleared_by_beta_is_persisted_as_kept(self) -> None:
        widgets = FakeWidgetRepository()
        checks = FakeOkBetaCheck()
        added = alpha_service.AlphaService(widgets, checks).add(add_request(name="a", part="a"))
        assert checks.checked == ["a"]
        assert added.standing == "kept"
        assert widgets.standing_by_name == {"a": "kept"}

    def test_a_held_part_refused_by_beta_is_persisted_as_released(self) -> None:
        widgets = FakeWidgetRepository()
        checks = FakeRefusedBetaCheck()
        added = alpha_service.AlphaService(widgets, checks).add(add_request(name="a", part="a"))
        assert checks.checked == ["a"]
        assert added.standing == "released"
        assert widgets.standing_by_name == {"a": "released"}
