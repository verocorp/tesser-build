from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.domain.widget as widget
import tesser.errors as errors


@ts.fake
class FakeWidgetRepository(widget_repository.WidgetRepository):

    def __init__(self, part_by_name: dict[str, str], saved: list[str]) -> None:
        self._part_by_name = part_by_name
        self._saved = saved

    async def save_widget(self, request: widget_repository.SaveWidgetRequest) -> widget_repository.SaveWidgetResponse:
        self._saved.append(request.name)
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
class FakeCommittedWidgetStore(widget_repository.WidgetStore):

    def __init__(self) -> None:
        self.part_by_name: dict[str, str] = {}
        self.saved: list[str] = []
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[widget_repository.WidgetRepository]:
        self.transactions += 1
        yield FakeWidgetRepository(self.part_by_name, self.saved)


@ts.fake
class FakeUnavailableWidgetStore(widget_repository.WidgetStore):

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[widget_repository.WidgetRepository]:
        raise errors.InfraError("widget store unavailable")
        yield FakeWidgetRepository({}, [])


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        self.checked.append(request.name)
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlphaServiceOverACommittedTransaction:

    async def test_a_new_part_is_taken_and_the_widget_saved_in_one_transaction(self) -> None:
        widget_store = FakeCommittedWidgetStore()
        checks = FakeBetaCheck()
        added = await alpha_service.AlphaService(widget_store, checks).add(client.AddRequest(name="a", part="p"))
        assert added.name == "a"
        assert widget_store.part_by_name == {"a": "p"}
        assert widget_store.transactions == 1
        assert checks.checked == []

    async def test_the_held_part_is_kept_and_the_widget_checked_outside_any_transaction(self) -> None:
        widget_store = FakeCommittedWidgetStore()
        checks = FakeBetaCheck()
        await alpha_service.AlphaService(widget_store, checks).add(client.AddRequest(name="a", part="a"))
        assert widget_store.part_by_name == {}
        assert widget_store.transactions == 0
        assert checks.checked == ["a"]

    async def test_take_loads_decides_and_saves_in_one_transaction(self) -> None:
        widget_store = FakeCommittedWidgetStore()
        service = alpha_service.AlphaService(widget_store, FakeBetaCheck())
        await service.add(client.AddRequest(name="a", part="p"))
        taken = await service.take(client.TakeRequest(name="a", part="q"))
        assert taken.part == "q"
        assert widget_store.part_by_name == {"a": "q"}
        assert widget_store.transactions == 2

    async def test_take_of_the_part_already_held_saves_nothing(self) -> None:
        widget_store = FakeCommittedWidgetStore()
        service = alpha_service.AlphaService(widget_store, FakeBetaCheck())
        await service.add(client.AddRequest(name="a", part="p"))
        taken = await service.take(client.TakeRequest(name="a", part="p"))
        assert taken.part == "p"
        assert widget_store.part_by_name == {"a": "p"}
        assert widget_store.saved == ["a"]

    async def test_take_of_an_unknown_widget_is_not_found(self) -> None:
        service = alpha_service.AlphaService(FakeCommittedWidgetStore(), FakeBetaCheck())
        with pytest.raises(errors.DomainError) as caught:
            await service.take(client.TakeRequest(name="x", part="q"))
        assert caught.value.kind is errors.Kind.NOT_FOUND

    async def test_find_reports_whether_the_store_holds_the_name(self) -> None:
        service = alpha_service.AlphaService(FakeCommittedWidgetStore(), FakeBetaCheck())
        await service.add(client.AddRequest(name="a", part="p"))
        found = await service.find(client.FindRequest(name="a"))
        missing = await service.find(client.FindRequest(name="x"))
        assert found.found == "yes"
        assert missing.found == "no"


class TestAlphaServiceOverAFailedTransaction:

    async def test_add_surfaces_the_failure(self) -> None:
        service = alpha_service.AlphaService(FakeUnavailableWidgetStore(), FakeBetaCheck())
        with pytest.raises(errors.InfraError):
            await service.add(client.AddRequest(name="a", part="p"))

    async def test_take_surfaces_the_failure(self) -> None:
        service = alpha_service.AlphaService(FakeUnavailableWidgetStore(), FakeBetaCheck())
        with pytest.raises(errors.InfraError):
            await service.take(client.TakeRequest(name="a", part="q"))

    async def test_find_surfaces_the_failure(self) -> None:
        service = alpha_service.AlphaService(FakeUnavailableWidgetStore(), FakeBetaCheck())
        with pytest.raises(errors.InfraError):
            await service.find(client.FindRequest(name="a"))

    async def test_a_held_part_still_reaches_beta_because_it_opens_no_transaction(self) -> None:
        checks = FakeBetaCheck()
        added = await alpha_service.AlphaService(FakeUnavailableWidgetStore(), checks).add(
            client.AddRequest(name="a", part="a")
        )
        assert added.name == "a"
        assert checks.checked == ["a"]


class TestAlphaServiceMappers:

    def test_an_add_request_maps_to_a_widget_spec_holding_its_own_name_as_the_part(self) -> None:
        spec = alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p"))
        assert spec.name == "a"
        assert spec.part.id == "a"

    def test_an_add_request_maps_to_the_part_it_names(self) -> None:
        assert alpha_service.MapToPartSpec(client.AddRequest(name="a", part="p")).id == "p"

    def test_a_take_request_maps_to_the_part_it_names(self) -> None:
        assert alpha_service.MapToTakenPartSpec(client.TakeRequest(name="a", part="q")).id == "q"

    def test_a_loaded_widget_maps_to_a_spec_carrying_its_stored_part(self) -> None:
        spec = alpha_service.MapToLoadedWidgetSpec(widget_repository.LoadWidgetResponse(name="a", part="p"))
        assert spec.name == "a"
        assert spec.part.id == "p"

    def test_a_widget_maps_to_a_save_request_carrying_its_name_and_part(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        request = alpha_service.MapToSaveWidgetRequest(built)
        assert request.name == "a"
        assert request.part == "a"

    def test_a_name_maps_to_a_load_request(self) -> None:
        assert alpha_service.MapToLoadWidgetRequest(widget.Name("a")).name == "a"

    def test_a_name_maps_to_a_find_request(self) -> None:
        assert alpha_service.MapToFindWidgetRequest(widget.Name("a")).name == "a"

    def test_a_widget_maps_to_a_check_request(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        assert alpha_service.MapToCheckRequest(built).name == "a"

    def test_a_widget_maps_to_an_add_response(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        assert alpha_service.MapToAddResponse(built).name == "a"

    def test_a_widget_maps_to_a_take_response_carrying_the_part_it_now_holds(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        built.take(alpha_service.MapToTakenPartSpec(client.TakeRequest(name="a", part="q")))
        response = alpha_service.MapToTakeResponse(built)
        assert response.name == "a"
        assert response.part == "q"
