from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import tesser.errors as errors


@ts.fake
class FakeWidgetRepository(widget_repository.WidgetRepository):

    def __init__(self, part_by_name: dict[str, str]) -> None:
        self._part_by_name = part_by_name

    async def save_widget(self, request: widget_repository.SaveWidgetRequest) -> widget_repository.SaveWidgetResponse:
        self._part_by_name[request.name] = request.part
        return widget_repository.SaveWidgetResponse(name=request.name)

    async def load_widget(self, request: widget_repository.LoadWidgetRequest) -> widget_repository.LoadWidgetResponse:
        if request.name not in self._part_by_name:
            raise errors.not_found("unknown_widget", f"no widget {request.name!r}")
        return widget_repository.LoadWidgetResponse(name=request.name, part=self._part_by_name[request.name])

    async def find_widget(self, request: widget_repository.FindWidgetRequest) -> widget_repository.FindWidgetResponse:
        found = widget_repository.Found.YES if request.name in self._part_by_name else widget_repository.Found.NO
        return widget_repository.FindWidgetResponse(found=found)


@ts.fake
class FakeWidgetStore(widget_repository.WidgetStore):

    def __init__(self) -> None:
        self.part_by_name: dict[str, str] = {}
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[widget_repository.WidgetRepository]:
        self.transactions += 1
        yield FakeWidgetRepository(self.part_by_name)


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


@ts.helper
def take_request(name: str = "a", part: str = "q") -> client.TakeRequest:
    return client.TakeRequest(name=name, part=part)


class TestAlphaService:

    async def test_add_answers_the_added_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetStore(), FakeBetaCheck())
        added = await service.add(add_request())
        assert added.name == "a"

    async def test_a_new_part_is_taken_and_the_widget_saved_in_one_transaction(self) -> None:
        widget_store = FakeWidgetStore()
        checks = FakeBetaCheck()
        await alpha_service.AlphaService(widget_store, checks).add(add_request(name="a", part="p"))
        assert widget_store.part_by_name == {"a": "p"}
        assert widget_store.transactions == 1
        assert checks.checked == []

    async def test_the_held_part_is_kept_and_the_widget_checked_outside_any_transaction(self) -> None:
        widget_store = FakeWidgetStore()
        checks = FakeBetaCheck()
        await alpha_service.AlphaService(widget_store, checks).add(add_request(name="a", part="a"))
        assert widget_store.part_by_name == {}
        assert widget_store.transactions == 0
        assert checks.checked == ["a"]

    async def test_take_loads_decides_and_saves_in_one_transaction(self) -> None:
        widget_store = FakeWidgetStore()
        service = alpha_service.AlphaService(widget_store, FakeBetaCheck())
        await service.add(add_request(name="a", part="p"))
        taken = await service.take(take_request(name="a", part="q"))
        assert taken.part == "q"
        assert widget_store.part_by_name == {"a": "q"}
        assert widget_store.transactions == 2

    async def test_take_of_the_held_part_changes_nothing(self) -> None:
        widget_store = FakeWidgetStore()
        service = alpha_service.AlphaService(widget_store, FakeBetaCheck())
        await service.add(add_request(name="a", part="p"))
        taken = await service.take(take_request(name="a", part="p"))
        assert taken.part == "p"
        assert widget_store.part_by_name == {"a": "p"}

    async def test_take_of_an_unknown_widget_is_not_found(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetStore(), FakeBetaCheck())
        with pytest.raises(errors.DomainError) as caught:
            await service.take(take_request(name="x"))
        assert caught.value.kind is errors.Kind.NOT_FOUND

    async def test_find_reports_whether_the_store_holds_the_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetStore(), FakeBetaCheck())
        await service.add(add_request(name="a", part="p"))
        found = await service.find(client.FindRequest(name="a"))
        missing = await service.find(client.FindRequest(name="x"))
        assert found.found == "yes"
        assert missing.found == "no"
