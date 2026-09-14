from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


@ts.fake
class FakeOrderActionsRunner(relays.OrderActionsRunner):

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
class FakeUnpricedOrderActionsRunner(relays.OrderActionsRunner):

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICE_NOT_FOUND,
            prices=(),
            reasons=(f"no price for sku {price_product_request.sku!r}",),
        )


@ts.helper
def confirm_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> relays.ConfirmOrderRequest:
    return relays.ConfirmOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestOrderOrchestrator:

    def test_confirming_totals_the_product_price_over_the_quantity(self) -> None:
        confirm_order_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeOrderActionsRunner()).confirm_order(
                confirm_order_request()
            )
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == "o1"
        assert confirm_order_response.confirmed_orders[0].total_cents == 750

    def test_confirming_prices_the_ordered_product(self) -> None:
        fake_order_actions_runner = FakeOrderActionsRunner()
        asyncio.run(
            orchestrators.OrderOrchestrator(fake_order_actions_runner).confirm_order(
                confirm_order_request(sku="gadget")
            )
        )
        assert fake_order_actions_runner.priced == ["gadget"]

    def test_a_price_that_was_not_found_is_that_outcome_carrying_the_reason(self) -> None:
        confirm_order_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeUnpricedOrderActionsRunner()).confirm_order(
                confirm_order_request(sku="nothing")
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
                    FakeOrderActionsRunner(cents=10**12)
                ).confirm_order(confirm_order_request())
            )
        assert "at most" in excinfo.value.message
