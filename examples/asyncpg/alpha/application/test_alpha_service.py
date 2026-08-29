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

    async def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self.saved.append(request.name)
        return widget_repository.SaveResponse(name=request.name)

    async def find(self, request: widget_repository.FindRequest) -> widget_repository.FindResponse:
        found = widget_repository.Found.YES if request.name in self.saved else widget_repository.Found.NO
        return widget_repository.FindResponse(found=found)


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        self.checked.append(request.name)
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


@ts.helper
def add_request(name: str = "a", part: str = "p") -> client.AddRequest:
    return client.AddRequest(name=name, part=part)


class TestAlphaService:

    async def test_add_answers_the_added_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetRepository(), FakeBetaCheck())
        added = await service.add(add_request())
        assert added.name == "a"

    async def test_a_new_part_is_taken_and_the_widget_saved(self) -> None:
        widgets = FakeWidgetRepository()
        checks = FakeBetaCheck()
        await alpha_service.AlphaService(widgets, checks).add(add_request(name="a", part="p"))
        assert widgets.saved == ["a"]
        assert checks.checked == []

    async def test_the_held_part_is_kept_and_the_widget_checked(self) -> None:
        widgets = FakeWidgetRepository()
        checks = FakeBetaCheck()
        await alpha_service.AlphaService(widgets, checks).add(add_request(name="a", part="a"))
        assert widgets.saved == []
        assert checks.checked == ["a"]

    async def test_find_reports_whether_the_repository_holds_the_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetRepository(), FakeBetaCheck())
        await service.add(add_request(name="a", part="p"))
        found = await service.find(client.FindRequest(name="a"))
        missing = await service.find(client.FindRequest(name="x"))
        assert found.found == "yes"
        assert missing.found == "no"
