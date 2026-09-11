from __future__ import annotations

import pytest

import ordering.application.relays as relays
import ordering.domain as domain
import ordering.application.ports as ports  # tesser:debt TB070


class TestPurchaseOrchestratorRequestSnapshot:

    def test_a_request_is_the_order_it_carries_and_nothing_more(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2))
        raw = relays.PurchaseOrchestratorRequestSnapshot().serialize(
            relays.PurchaseOrchestratorRequest(order=order)
        )
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_a_request_comes_back_around_its_order(self) -> None:
        purchase_orchestrator_request_snapshot = relays.PurchaseOrchestratorRequestSnapshot()
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        purchase_orchestrator_request = purchase_orchestrator_request_snapshot.deserialize(
            purchase_orchestrator_request_snapshot.serialize(
                relays.PurchaseOrchestratorRequest(order=order)
            )
        )
        assert purchase_orchestrator_request.order.identity == domain.OrderId("o7")
        assert purchase_orchestrator_request.order.sku == domain.Sku("gadget")
        assert purchase_orchestrator_request.order.quantity == domain.Quantity(3)


class TestPurchaseOrchestratorResponseSnapshot:

    def test_a_response_is_the_order_id_the_total_and_the_payment_reference(self) -> None:
        purchase_orchestrator_response = relays.PurchaseOrchestratorResponse(
            order_id="o1", total_cents=500, payment_reference="pay-o1"
        )
        assert relays.PurchaseOrchestratorResponseSnapshot().serialize(
            purchase_orchestrator_response
        ) == b'{"order_id": "o1", "total_cents": 500, "payment_reference": "pay-o1"}'

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1", "total_cents": 500}',
            b'{"order_id": "", "total_cents": 500, "payment_reference": "pay-o1"}',
            b'{"order_id": "o1", "total_cents": 500, "payment_reference": ""}',
            b'{"order_id": "o1", "total_cents": -1, "payment_reference": "pay-o1"}',
            b'{"order_id": "o1", "total_cents": true, "payment_reference": "pay-o1"}',
            b'{"order_id": "o1", "total_cents": "500", "payment_reference": "pay-o1"}',
            b'{"order_id": "o1", "total_cents": 500, "payment_reference": 7}',
            b'{"order_id": {}, "total_cents": 500, "payment_reference": "pay-o1"}',
            b'["o1", 500, "pay-o1"]',
        ):
            with pytest.raises(ports.EngineRejected):
                relays.PurchaseOrchestratorResponseSnapshot().deserialize(raw)

    def test_a_response_comes_back_equal(self) -> None:
        purchase_orchestrator_response_snapshot = relays.PurchaseOrchestratorResponseSnapshot()
        purchase_orchestrator_response = relays.PurchaseOrchestratorResponse(
            order_id="o7", total_cents=750, payment_reference="pay-o7"
        )
        assert purchase_orchestrator_response_snapshot.deserialize(
            purchase_orchestrator_response_snapshot.serialize(purchase_orchestrator_response)
        ) == purchase_orchestrator_response
