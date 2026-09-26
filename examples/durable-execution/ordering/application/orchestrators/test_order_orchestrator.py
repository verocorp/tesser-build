from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


@ts.fake
class FakeOrderActionsRelay(relays.OrderActionsRelay):

    def __init__(self, cents: int = 250) -> None:
        self._cents = cents
        self.priced: list[str] = []

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        self.priced.append(price_product_request.sku)
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=self._cents),),
            reasons=(),
        )


@ts.fake
class FakeUnpricedOrderActionsRelay(relays.OrderActionsRelay):

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICE_NOT_FOUND,
            prices=(),
            reasons=(f"no price for sku {price_product_request.sku!r}",),
        )


@ts.helper
def order_spec(order_id: str = "o1", sku: str = "widget", quantity: int = 3) -> domain.OrderSpec:
    return domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_confirmation_leaves_the_journaled_order_input_whole(self) -> None:
        order = domain.Order(order_spec())
        confirm_order_request = relays.ConfirmOrderRequest(order=order)
        confirm_order_request_snapshot = relays.ConfirmOrderRequestSnapshot()
        raw = confirm_order_request_snapshot.serialize(confirm_order_request)
        confirm_order_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeOrderActionsRelay()).confirm_order(
                confirm_order_request
            )
        )
        assert confirm_order_response.confirmed_orders[0].total_cents == 750
        assert confirm_order_request_snapshot.serialize(confirm_order_request) == raw
        restored_order = confirm_order_request_snapshot.deserialize(raw).order
        assert restored_order.identity == order.identity
        assert restored_order.sku == order.sku
        assert restored_order.quantity == order.quantity

    def test_confirming_totals_the_product_price_over_the_quantity(self) -> None:
        confirm_order_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeOrderActionsRelay()).confirm_order(
                relays.ConfirmOrderRequest(order=domain.Order(order_spec(order_id="o1", quantity=3)))
            )
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == "o1"
        assert confirm_order_response.confirmed_orders[0].total_cents == 750

    def test_confirming_prices_the_ordered_product(self) -> None:
        fake_order_actions_relay = FakeOrderActionsRelay()
        asyncio.run(
            orchestrators.OrderOrchestrator(fake_order_actions_relay).confirm_order(
                relays.ConfirmOrderRequest(order=domain.Order(order_spec(sku="gadget")))
            )
        )
        assert fake_order_actions_relay.priced == ["gadget"]

    def test_a_price_that_was_not_found_is_that_outcome_carrying_the_reason(self) -> None:
        confirm_order_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeUnpricedOrderActionsRelay()).confirm_order(
                relays.ConfirmOrderRequest(order=domain.Order(order_spec(sku="nothing")))
            )
        )
        assert (
            confirm_order_response.outcome
            is relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
        )
        assert confirm_order_response.confirmed_orders == ()
        assert confirm_order_response.reasons == ("no price for sku 'nothing'",)

    def test_a_total_past_the_domains_bound_is_a_fault(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.OrderOrchestrator(
                    FakeOrderActionsRelay(cents=10**12)
                ).confirm_order(relays.ConfirmOrderRequest(order=domain.Order(order_spec())))
            )
        assert "at most" in excinfo.value.message
