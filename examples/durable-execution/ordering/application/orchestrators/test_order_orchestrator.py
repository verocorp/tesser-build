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

    def __init__(self) -> None:
        self.priced: list[str] = []

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        self.priced.append(price_product_request.sku)
        return relays.PriceProductResponse(cents=250)


@ts.fake
class FakeRefusingOrderActionsRunner(relays.OrderActionsRunner):

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        raise errors.not_found("unknown_sku", f"no price for sku {price_product_request.sku!r}")


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestOrderOrchestrator:

    def test_running_totals_the_product_price_over_the_quantity(self) -> None:
        order_orchestrator_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeOrderActionsRunner()).run(
                order_orchestrator_request()
            )
        )
        assert order_orchestrator_response.order_id == "o1"
        assert order_orchestrator_response.total_cents == 750

    def test_running_prices_the_ordered_product(self) -> None:
        fake_order_actions_runner = FakeOrderActionsRunner()
        asyncio.run(
            orchestrators.OrderOrchestrator(fake_order_actions_runner).run(
                order_orchestrator_request(sku="gadget")
            )
        )
        assert fake_order_actions_runner.priced == ["gadget"]

    def test_a_refused_price_ends_the_run_with_the_actions_error(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.OrderOrchestrator(FakeRefusingOrderActionsRunner()).run(
                    order_orchestrator_request(sku="nothing")
                )
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
