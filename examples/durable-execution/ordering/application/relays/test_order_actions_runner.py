from __future__ import annotations

import pytest

import ordering.application.relays as relays


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

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (b'{}', b'{"sku": 1}', b'{"sku": ""}', b'["widget"]'):
            with pytest.raises(ValueError):
                relays.PriceProductRequestSnapshot().deserialize(raw)


class TestPriceProductResponseSnapshot:

    def test_a_priced_response_is_its_outcome_and_the_one_price(self) -> None:
        raw = relays.PriceProductResponseSnapshot().serialize(
            relays.PriceProductResponse(
                outcome=relays.PriceProductOutcome.PRICED,
                prices=(relays.Price(cents=250),),
                reasons=(),
            )
        )
        assert raw == b'{"outcome": "priced", "prices": [{"cents": 250}], "reasons": []}'

    def test_a_price_that_was_not_found_carries_no_price_and_its_reason(self) -> None:
        raw = relays.PriceProductResponseSnapshot().serialize(
            relays.PriceProductResponse(
                outcome=relays.PriceProductOutcome.PRICE_NOT_FOUND,
                prices=(),
                reasons=("no price for sku 'nope'",),
            )
        )
        assert raw == (
            b'{"outcome": "price_not_found", "prices": [], '
            b'"reasons": ["no price for sku \'nope\'"]}'
        )

    def test_a_response_comes_back_equal(self) -> None:
        price_product_response_snapshot = relays.PriceProductResponseSnapshot()
        price_product_response = relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )
        assert price_product_response_snapshot.deserialize(
            price_product_response_snapshot.serialize(price_product_response)
        ) == price_product_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{}',
            b'{"outcome": "priced", "prices": [{"cents": -1}], "reasons": []}',
            b'{"outcome": "priced", "prices": [{"cents": true}], "reasons": []}',
            b'{"outcome": "priced", "prices": [{"cents": "250"}], "reasons": []}',
            b'{"outcome": "unpriced", "prices": [], "reasons": []}',
            b'{"outcome": "priced", "prices": [], "reasons": []}',
            b'{"outcome": "price_not_found", "prices": [{"cents": 250}], "reasons": []}',
            b'{"outcome": "priced", "prices": [{"cents": 250}], "reasons": [7]}',
            b'[250]',
        ):
            with pytest.raises(ValueError):
                relays.PriceProductResponseSnapshot().deserialize(raw)
