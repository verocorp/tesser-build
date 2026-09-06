from __future__ import annotations

import pytest

import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


class TestOrderSnapshot:

    def test_the_snapshot_is_the_orders_canonical_form(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2, note="gift"))
        assert relays.OrderSnapshot().serialize(order) == b'{"order_id": "o1", "sku": "widget", "quantity": 2, "note": "gift"}'

    def test_an_order_comes_back_whole_through_its_own_constructor(self) -> None:
        order_snapshot = relays.OrderSnapshot()  # tesser:debt TB085
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3, note="fragile"))
        back = order_snapshot.deserialize(order_snapshot.serialize(order))
        assert back.identity == domain.OrderId("o7")
        assert back.sku == domain.Sku("gadget")
        assert back.quantity == domain.Quantity(3)
        assert back.note == domain.Note("fragile")

    def test_a_snapshot_that_breaks_an_invariant_is_refused_on_the_way_in(self) -> None:
        with pytest.raises(errors.DomainError):
            relays.OrderSnapshot().deserialize(
                b'{"order_id": "o1", "sku": "widget", "quantity": 0, "note": "gift"}'
            )

    def test_a_snapshot_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1", "sku": [1, 2], "quantity": 2, "note": "gift"}',
            b'{"order_id": "o1", "sku": "widget", "quantity": true, "note": "gift"}',
            b'{"order_id": "o1", "sku": "widget", "quantity": "2", "note": "gift"}',
            b'{"order_id": "o1", "sku": "widget", "quantity": 2, "note": 7}',
            b'{"order_id": "o1", "sku": "widget", "quantity": 2}',
            b'{"order_id": "o1", "sku": "widget", "note": "gift"}',
            b'["o1", "widget", 2, "gift"]',
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                relays.OrderSnapshot().deserialize(raw)
            assert excinfo.value.kind is errors.Kind.VALIDATION


class TestOrderOrchestratorRequestSnapshot:

    def test_a_request_is_the_order_it_carries_and_nothing_more(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2, note="gift"))
        raw = relays.OrderOrchestratorRequestSnapshot().serialize(
            relays.OrderOrchestratorRequest(order=order)
        )
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2, "note": "gift"}'

    def test_a_request_comes_back_around_its_order(self) -> None:
        order_orchestrator_request_snapshot = relays.OrderOrchestratorRequestSnapshot()  # tesser:debt TB085
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3, note="fragile"))
        back = order_orchestrator_request_snapshot.deserialize(
            order_orchestrator_request_snapshot.serialize(
                relays.OrderOrchestratorRequest(order=order)
            )
        )
        assert back.order.identity == domain.OrderId("o7")
        assert back.order.sku == domain.Sku("gadget")
        assert back.order.quantity == domain.Quantity(3)
        assert back.order.note == domain.Note("fragile")


class TestOrderOrchestratorResponseSnapshot:

    def test_a_response_is_the_order_id_and_the_total(self) -> None:
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
        assert relays.OrderOrchestratorResponseSnapshot().serialize(
            order_orchestrator_response
        ) == b'{"order_id": "o1", "total_cents": 500}'

    def test_a_response_comes_back_equal(self) -> None:
        order_orchestrator_response_snapshot = relays.OrderOrchestratorResponseSnapshot()  # tesser:debt TB085
        order_orchestrator_response = relays.OrderOrchestratorResponse(order_id="o7", total_cents=750)
        assert order_orchestrator_response_snapshot.deserialize(
            order_orchestrator_response_snapshot.serialize(order_orchestrator_response)
        ) == order_orchestrator_response
