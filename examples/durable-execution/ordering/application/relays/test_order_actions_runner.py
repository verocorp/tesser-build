from __future__ import annotations

import pytest

import ordering.application.relays as relays
import ordering.application.ports as ports  # tesser:debt TB070


class TestPriceProductRequestSnapshot:

    def test_a_request_is_its_sku(self) -> None:
        raw = relays.PriceProductRequestSnapshot().serialize(relays.PriceProductRequest(sku="widget"))
        assert raw == b'{"sku": "widget"}'

    def test_a_request_comes_back_equal(self) -> None:
        price_product_request_snapshot = relays.PriceProductRequestSnapshot()
        price_product_request = relays.PriceProductRequest(sku="gadget")
        assert price_product_request_snapshot.deserialize(
            price_product_request_snapshot.serialize(price_product_request)
        ) == price_product_request


class TestPriceProductResponseSnapshot:

    def test_a_response_is_its_cents(self) -> None:
        raw = relays.PriceProductResponseSnapshot().serialize(relays.PriceProductResponse(cents=250))
        assert raw == b'{"cents": 250}'

    def test_a_response_comes_back_equal(self) -> None:
        price_product_response_snapshot = relays.PriceProductResponseSnapshot()
        price_product_response = relays.PriceProductResponse(cents=250)
        assert price_product_response_snapshot.deserialize(
            price_product_response_snapshot.serialize(price_product_response)
        ) == price_product_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{}',
            b'{"cents": -1}',
            b'{"cents": true}',
            b'{"cents": "250"}',
            b'[250]',
        ):
            with pytest.raises(ports.EngineRejected):
                relays.PriceProductResponseSnapshot().deserialize(raw)


class TestPriceProductRequestSnapshotShape:

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b'{}', b'{"sku": 1}', b'{"sku": ""}', b'["widget"]'):
            with pytest.raises(ports.EngineRejected):
                relays.PriceProductRequestSnapshot().deserialize(raw)
