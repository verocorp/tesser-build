from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client
import alpha.domain as domain


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(
        self, part_by_name: dict[str, str], standing_by_name: dict[str, str], saved: list[str]
    ) -> None:
        self._part_by_name = part_by_name
        self._standing_by_name = standing_by_name
        self._saved = saved

    async def add_widget(self, add_widget_request: ports.AddWidgetRequest) -> ports.AddWidgetResponse:
        if add_widget_request.name in self._part_by_name:
            return ports.AddWidgetResponse(
                outcome=ports.AddWidgetOutcome.EXISTS, name=add_widget_request.name
            )
        self._saved.append(add_widget_request.name)
        self._part_by_name[add_widget_request.name] = add_widget_request.part
        self._standing_by_name[add_widget_request.name] = add_widget_request.standing
        return ports.AddWidgetResponse(
            outcome=ports.AddWidgetOutcome.ADDED, name=add_widget_request.name
        )

    async def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        self._saved.append(save_widget_request.name)
        self._part_by_name[save_widget_request.name] = save_widget_request.part
        self._standing_by_name[save_widget_request.name] = save_widget_request.standing
        return ports.SaveWidgetResponse(name=save_widget_request.name)

    async def load_widget(self, load_widget_request: ports.LoadWidgetRequest) -> ports.LoadWidgetResponse:
        if load_widget_request.name not in self._part_by_name:
            return ports.LoadWidgetResponse(outcome=ports.LoadWidgetOutcome.NOT_FOUND, widgets=())
        return ports.LoadWidgetResponse(
            outcome=ports.LoadWidgetOutcome.FOUND,
            widgets=(
                ports.WidgetRecord(
                    name=load_widget_request.name,
                    part=self._part_by_name[load_widget_request.name],
                    standing=self._standing_by_name[load_widget_request.name],
                ),
            ),
        )

    async def find_widget(self, find_widget_request: ports.FindWidgetRequest) -> ports.FindWidgetResponse:
        outcome = ports.FindWidgetOutcome.YES if find_widget_request.name in self._part_by_name else ports.FindWidgetOutcome.NO
        return ports.FindWidgetResponse(outcome=outcome)


@ts.fake
class FakeCommittedWidgetStore(ports.WidgetStore):

    def __init__(self) -> None:
        self.part_by_name: dict[str, str] = {}
        self.standing_by_name: dict[str, str] = {}
        self.saved: list[str] = []
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.WidgetRepository]:
        self.transactions += 1
        yield FakeWidgetRepository(self.part_by_name, self.standing_by_name, self.saved)


@ts.fake
class FakeOkBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    async def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        self.checked.append(check_name_request.name)
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.OK)


@ts.fake
class FakeRefusedBetaCheck(ports.BetaCheck):

    def __init__(self) -> None:
        self.checked: list[str] = []

    async def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        self.checked.append(check_name_request.name)
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.REFUSED)


class TestAlphaServiceOverACommittedTransaction:

    async def test_a_new_part_is_taken_and_the_widget_saved_kept_in_one_transaction(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = await application.AlphaService(
            fake_committed_widget_store, fake_ok_beta_check
        ).add_part(client.AddPartRequest(name="a", part="p"))
        assert add_part_response.name == "a"
        assert add_part_response.standing == "kept"
        assert fake_committed_widget_store.part_by_name == {"a": "p"}
        assert fake_committed_widget_store.standing_by_name == {"a": "kept"}
        assert fake_committed_widget_store.transactions == 1
        assert fake_ok_beta_check.checked == []

    async def test_a_held_part_cleared_by_beta_is_persisted_as_kept(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        fake_ok_beta_check = FakeOkBetaCheck()
        add_part_response = await application.AlphaService(
            fake_committed_widget_store, fake_ok_beta_check
        ).add_part(client.AddPartRequest(name="a", part="a"))
        assert fake_ok_beta_check.checked == ["a"]
        assert add_part_response.standing == "kept"
        assert fake_committed_widget_store.standing_by_name == {"a": "kept"}
        assert fake_committed_widget_store.transactions == 1

    async def test_a_held_part_refused_by_beta_is_persisted_as_released(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        fake_refused_beta_check = FakeRefusedBetaCheck()
        add_part_response = await application.AlphaService(
            fake_committed_widget_store, fake_refused_beta_check
        ).add_part(client.AddPartRequest(name="a", part="a"))
        assert fake_refused_beta_check.checked == ["a"]
        assert add_part_response.standing == "released"
        assert fake_committed_widget_store.standing_by_name == {"a": "released"}
        assert fake_committed_widget_store.transactions == 1

    async def test_a_released_widget_reloads_released(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        alpha_service = application.AlphaService(fake_committed_widget_store, FakeRefusedBetaCheck())
        await alpha_service.add_part(client.AddPartRequest(name="a", part="a"))
        take_part_response = await alpha_service.take_part(
            client.TakePartRequest(name="a", part="q")
        )
        assert take_part_response.standing == "released"

    async def test_take_loads_decides_and_saves_in_one_transaction(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        alpha_service = application.AlphaService(fake_committed_widget_store, FakeOkBetaCheck())
        await alpha_service.add_part(client.AddPartRequest(name="a", part="p"))
        take_part_response = await alpha_service.take_part(
            client.TakePartRequest(name="a", part="q")
        )
        assert take_part_response.part == "q"
        assert fake_committed_widget_store.part_by_name == {"a": "q"}
        assert fake_committed_widget_store.transactions == 2

    async def test_take_of_the_part_already_held_saves_nothing(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        alpha_service = application.AlphaService(fake_committed_widget_store, FakeOkBetaCheck())
        await alpha_service.add_part(client.AddPartRequest(name="a", part="p"))
        take_part_response = await alpha_service.take_part(
            client.TakePartRequest(name="a", part="p")
        )
        assert take_part_response.part == "p"
        assert fake_committed_widget_store.part_by_name == {"a": "p"}
        assert fake_committed_widget_store.saved == ["a"]

    async def test_take_of_an_unknown_widget_crosses_as_widget_not_found(self) -> None:
        alpha_service = application.AlphaService(FakeCommittedWidgetStore(), FakeOkBetaCheck())
        with pytest.raises(client.WidgetNotFound) as caught:
            await alpha_service.take_part(client.TakePartRequest(name="x", part="q"))
        assert caught.value.message == "no widget 'x'"

    async def test_adding_a_stored_name_is_widget_exists_and_leaves_the_stored_widget_alone(self) -> None:
        fake_committed_widget_store = FakeCommittedWidgetStore()
        alpha_service = application.AlphaService(fake_committed_widget_store, FakeRefusedBetaCheck())
        add_part_response = await alpha_service.add_part(client.AddPartRequest(name="a", part="a"))
        with pytest.raises(client.WidgetExists) as caught:
            await alpha_service.add_part(client.AddPartRequest(name="a", part="q"))
        assert add_part_response.standing == "released"
        assert caught.value.message == "widget 'a' is already stored"
        assert fake_committed_widget_store.part_by_name == {"a": "a"}
        assert fake_committed_widget_store.standing_by_name == {"a": "released"}

    async def test_find_reports_whether_the_store_holds_the_name(self) -> None:
        alpha_service = application.AlphaService(FakeCommittedWidgetStore(), FakeOkBetaCheck())
        await alpha_service.add_part(client.AddPartRequest(name="a", part="p"))
        found = await alpha_service.find_widget(client.FindWidgetRequest(name="a"))
        missing = await alpha_service.find_widget(client.FindWidgetRequest(name="x"))
        assert found.found == "yes"
        assert missing.found == "no"


class TestAlphaServiceMappers:

    def test_an_add_request_maps_to_a_widget_spec_holding_its_own_name_as_the_part(self) -> None:
        widget_spec = application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        assert widget_spec.name == "a"
        assert widget_spec.part.id == "a"
        assert widget_spec.standing == "kept"

    def test_an_add_request_maps_to_the_part_it_names(self) -> None:
        assert application.MapToPartSpec(client.AddPartRequest(name="a", part="p")).id == "p"

    def test_a_take_request_maps_to_the_part_it_names(self) -> None:
        assert (
            application.MapToTakenPartSpec(client.TakePartRequest(name="a", part="q")).id == "q"
        )

    def test_a_loaded_widget_maps_to_a_spec_carrying_its_stored_part(self) -> None:
        widget_spec = application.MapToLoadedWidgetSpec(
            ports.LoadWidgetRequest(name="a"),
            ports.LoadWidgetResponse(
                outcome=ports.LoadWidgetOutcome.FOUND,
                widgets=(ports.WidgetRecord(name="a", part="p", standing="released"),),
            ),
        )
        assert widget_spec.name == "a"
        assert widget_spec.part.id == "p"
        assert widget_spec.standing == "released"

    def test_a_lookup_that_is_not_found_is_widget_not_found_naming_the_widget(self) -> None:
        with pytest.raises(client.WidgetNotFound) as caught:
            application.MapToLoadedWidgetSpec(
                ports.LoadWidgetRequest(name="x"),
                ports.LoadWidgetResponse(outcome=ports.LoadWidgetOutcome.NOT_FOUND, widgets=()),
            )
        assert caught.value.message == "no widget 'x'"

    def test_a_widget_maps_to_a_save_request_carrying_its_name_and_part(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        save_widget_request = application.MapToSaveWidgetRequest(widget)
        assert save_widget_request.name == "a"
        assert save_widget_request.part == "a"
        assert save_widget_request.standing == "kept"

    def test_a_name_maps_to_a_load_request(self) -> None:
        assert application.MapToLoadWidgetRequest(domain.Name("a")).name == "a"

    def test_a_name_maps_to_a_find_request(self) -> None:
        assert application.MapToFindWidgetRequest(domain.Name("a")).name == "a"

    def test_a_widget_maps_to_a_check_request(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        assert application.MapToCheckNameRequest(widget).name == "a"

    def test_a_check_response_maps_to_a_clearance_spec_carrying_its_verdict(self) -> None:
        check_name_response = ports.CheckNameResponse(outcome=ports.CheckNameOutcome.REFUSED)
        assert application.MapToClearanceSpec(check_name_response).verdict == "refused"

    def test_a_stored_widget_maps_to_an_add_response(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        add_widget_response = ports.AddWidgetResponse(outcome=ports.AddWidgetOutcome.ADDED, name="a")
        assert application.MapToAddPartResponse(add_widget_response, widget).name == "a"
        assert application.MapToAddPartResponse(add_widget_response, widget).part == "a"
        assert application.MapToAddPartResponse(add_widget_response, widget).standing == "kept"

    def test_a_name_the_store_already_holds_is_widget_exists(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        add_widget_response = ports.AddWidgetResponse(outcome=ports.AddWidgetOutcome.EXISTS, name="a")
        with pytest.raises(client.WidgetExists) as caught:
            application.MapToAddPartResponse(add_widget_response, widget)
        assert caught.value.message == "widget 'a' is already stored"

    def test_a_widget_maps_to_an_add_widget_request(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        add_widget_request = application.MapToAddWidgetRequest(widget)
        assert add_widget_request.name == "a"
        assert add_widget_request.part == "a"
        assert add_widget_request.standing == "kept"

    def test_a_widget_maps_to_a_take_response_carrying_the_part_it_now_holds(self) -> None:
        widget = domain.Widget(
            application.MapToWidgetSpec(client.AddPartRequest(name="a", part="p"))
        )
        widget.take(application.MapToTakenPartSpec(client.TakePartRequest(name="a", part="q")))
        take_part_response = application.MapToTakePartResponse(widget)
        assert take_part_response.name == "a"
        assert take_part_response.part == "q"
        assert take_part_response.standing == "kept"
