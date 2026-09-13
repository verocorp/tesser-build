from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client


@ts.fake
class FakeOrderOrchestratorRunner(relays.OrderOrchestratorRunner):

    def __init__(self) -> None:
        self.started: list[relays.ConfirmOrderRequest] = []
        self.ran: list[relays.ConfirmOrderRequest] = []

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        self.started.append(confirm_order_request)
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        self.ran.append(confirm_order_request)
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(
                relays.ConfirmedOrder(
                    total_cents=250 * int(confirm_order_request.order.quantity)
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeUnpricedOrderOrchestratorRunner(relays.OrderOrchestratorRunner):

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(),
            reasons=(f"no price for sku {confirm_order_request.order.sku!s}",),
        )


@ts.fake
class FakeStartedOrderOrchestratorRunner(relays.OrderOrchestratorRunner):

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.ALREADY_STARTED,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(),
            reasons=("the workflow method was already invoked",),
        )


@ts.helper
def submit_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> client.SubmitOrderRequest:
    return client.SubmitOrderRequest(order_id=order_id, sku=sku, quantity=quantity)


@ts.helper
def place_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> client.PlaceOrderRequest:
    return client.PlaceOrderRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderService:

    def test_submitting_answers_the_order_id(self) -> None:
        submit_order_response = asyncio.run(
            application.OrderService(FakeOrderOrchestratorRunner()).submit_order(
                submit_order_request()
            )
        )
        assert submit_order_response.order_id == "o1"

    def test_submitting_starts_confirming_the_order_it_built(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()
        asyncio.run(
            application.OrderService(fake_order_orchestrator_runner).submit_order(
                submit_order_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(s.order.identity), str(s.order.sku), int(s.order.quantity))
            for s in fake_order_orchestrator_runner.started
        ] == [("o2", "gadget", 3)]

    def test_an_order_the_domain_refuses_never_reaches_the_engine(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()
        with pytest.raises(client.OrderRejected) as excinfo:
            asyncio.run(
                application.OrderService(fake_order_orchestrator_runner).submit_order(
                    submit_order_request(quantity=0)
                )
            )
        assert excinfo.value.message == "an order is for at least one unit"
        assert fake_order_orchestrator_runner.started == []

    def test_placing_answers_the_order_id_and_the_total(self) -> None:
        place_order_response = asyncio.run(
            application.OrderService(FakeOrderOrchestratorRunner()).place_order(
                place_order_request(quantity=3)
            )
        )
        assert place_order_response.order_id == "o1"
        assert place_order_response.total_cents == 750

    def test_placing_runs_confirming_the_order_it_built_and_waits(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()
        asyncio.run(
            application.OrderService(fake_order_orchestrator_runner).place_order(
                place_order_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(r.order.identity), str(r.order.sku), int(r.order.quantity))
            for r in fake_order_orchestrator_runner.ran
        ] == [("o2", "gadget", 3)]
        assert fake_order_orchestrator_runner.started == []

    def test_a_product_price_that_was_not_found_is_the_situation_of_that_name(self) -> None:
        with pytest.raises(client.ProductPriceNotFound) as excinfo:
            asyncio.run(
                application.OrderService(FakeUnpricedOrderOrchestratorRunner()).place_order(
                    place_order_request(sku="nothing")
                )
            )
        assert excinfo.value.message == "no price for sku nothing"

    def test_an_order_already_started_is_the_situation_of_that_name(self) -> None:
        with pytest.raises(client.OrderAlreadyStarted) as excinfo:
            asyncio.run(
                application.OrderService(FakeStartedOrderOrchestratorRunner()).place_order(
                    place_order_request()
                )
            )
        assert excinfo.value.message == "the workflow method was already invoked"
