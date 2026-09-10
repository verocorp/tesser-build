from __future__ import annotations

import asyncio

import tesser.testing as ts
import pytest

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays  # tesser:debt TB070
import ordering.domain as domain
import tesser.errors as errors


@ts.fake
class FakePurchaseActionsRunner(relays.PurchaseActionsRunner):

    def __init__(self, cents_charged: int = 0, order_charged: str = "") -> None:
        self._cents_charged = cents_charged
        self._order_charged = order_charged
        self.taken: list[tuple[str, int]] = []

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        self.taken.append((take_payment_request.order_id, take_payment_request.cents))
        order_id = self._order_charged or take_payment_request.order_id
        return relays.TakePaymentResponse(
            order_id=order_id,
            reference=f"pay-{order_id}",
            cents=self._cents_charged or take_payment_request.cents,
        )


@ts.fake
class FakeOrderOrchestratorRunner(relays.OrderOrchestratorRunner):  # tesser:debt TB072

    def __init__(self) -> None:
        self.started: list[str] = []
        self.ran: list[str] = []

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        self.started.append(str(order_orchestrator_request.order.identity))
        return relays.StartOrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity)
        )

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        self.ran.append(str(order_orchestrator_request.order.identity))
        return relays.OrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity),
            total_cents=250 * int(order_orchestrator_request.order.quantity),
        )


@ts.fake
class FakeMisroutedOrderOrchestratorRunner(relays.OrderOrchestratorRunner):  # tesser:debt TB072

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        return relays.StartOrderOrchestratorResponse(order_id="other")

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        return relays.OrderOrchestratorResponse(order_id="other", total_cents=1)


@ts.fake
class FakeRefusingOrderOrchestratorRunner(relays.OrderOrchestratorRunner):  # tesser:debt TB072

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        raise errors.not_found("unknown_sku", f"no price for sku {order_orchestrator_request.order.sku!s}")

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        raise errors.not_found("unknown_sku", f"no price for sku {order_orchestrator_request.order.sku!s}")


@ts.helper
def purchase_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> relays.PurchaseOrchestratorRequest:
    return relays.PurchaseOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestPurchaseOrchestrator:

    def test_running_answers_the_order_its_total_and_the_payment_taken(self) -> None:
        purchase_orchestrator_response = asyncio.run(
            orchestrators.PurchaseOrchestrator(
                FakePurchaseActionsRunner(), FakeOrderOrchestratorRunner()
            ).run(purchase_orchestrator_request())
        )
        assert purchase_orchestrator_response.order_id == "o1"
        assert purchase_orchestrator_response.total_cents == 750
        assert purchase_orchestrator_response.payment_reference == "pay-o1"

    def test_running_runs_the_order_as_a_child_and_then_takes_payment_for_its_total(self) -> None:
        fake_purchase_actions_runner = FakePurchaseActionsRunner()
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()  # tesser:debt TB085
        asyncio.run(
            orchestrators.PurchaseOrchestrator(
                fake_purchase_actions_runner, fake_order_orchestrator_runner
            ).run(purchase_orchestrator_request(order_id="o2", quantity=4))
        )
        assert fake_order_orchestrator_runner.ran == ["o2"]
        assert fake_order_orchestrator_runner.started == []
        assert fake_purchase_actions_runner.taken == [("o2", 1000)]

    def test_a_payment_of_another_amount_ends_the_run_as_a_conflict(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    FakePurchaseActionsRunner(cents_charged=700), FakeOrderOrchestratorRunner()
                ).run(purchase_orchestrator_request())
            )
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_mismatch"

    def test_a_refused_child_order_ends_the_run_before_any_payment(self) -> None:
        fake_purchase_actions_runner = FakePurchaseActionsRunner()
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    fake_purchase_actions_runner, FakeRefusingOrderOrchestratorRunner()
                ).run(purchase_orchestrator_request(sku="nothing"))
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
        assert fake_purchase_actions_runner.taken == []

    def test_a_child_that_answered_for_another_order_ends_the_run_before_any_payment(self) -> None:
        fake_purchase_actions_runner = FakePurchaseActionsRunner()
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    fake_purchase_actions_runner, FakeMisroutedOrderOrchestratorRunner()
                ).run(purchase_orchestrator_request())
            )
        assert excinfo.value.code == "priced_another_order"
        assert fake_purchase_actions_runner.taken == []

    def test_a_receipt_for_another_order_ends_the_run_as_a_conflict(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(
                orchestrators.PurchaseOrchestrator(
                    FakePurchaseActionsRunner(order_charged="other"), FakeOrderOrchestratorRunner()
                ).run(purchase_orchestrator_request())
            )
        assert excinfo.value.code == "payment_for_another_order"
