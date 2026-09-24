from __future__ import annotations

import contextlib
import typing

import tesser.testing as ts

import alpha.application as application
import alpha.application.ports as ports
import alpha.application.relays as relays


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []

    async def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        self.saved.append((save_widget_request.name, save_widget_request.standing))
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


class TestWidgetActions:

    async def test_keeping_saves_the_widget_once_standing_kept_and_answers_its_name(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        keep_widget_response = await application.WidgetActions(FakeWidgetStore(fake_widget_repository)).keep_widget(
            relays.KeepWidgetRequest(name="a")
        )
        assert keep_widget_response.name == "a"
        assert fake_widget_repository.saved == [("a", "kept")]
