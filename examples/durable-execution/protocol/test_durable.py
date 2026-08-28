from __future__ import annotations

import dataclasses

import pytest
import restate.serde

import protocol.durable as durable


class TestRunRequest:

    def test_the_sdk_serde_round_trips_it(self) -> None:
        serde: restate.serde.DefaultSerde[durable.RunRequest] = restate.serde.DefaultSerde(
            durable.RunRequest
        )
        assert serde.deserialize(serde.serialize(durable.RunRequest(sku="widget", quantity=2))) == (
            durable.RunRequest(sku="widget", quantity=2)
        )

    def test_it_is_frozen(self) -> None:
        request = durable.RunRequest(sku="widget", quantity=2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            request.sku = "gadget"  # type: ignore[misc]


class TestRunResponse:

    def test_the_sdk_serde_round_trips_it(self) -> None:
        serde: restate.serde.DefaultSerde[durable.RunResponse] = restate.serde.DefaultSerde(
            durable.RunResponse
        )
        answered = durable.RunResponse(order_id="o1", total_cents=2000)
        assert serde.deserialize(serde.serialize(answered)) == answered


class TestQuoteRequest:

    def test_the_sdk_serde_round_trips_it(self) -> None:
        serde: restate.serde.DefaultSerde[durable.QuoteRequest] = restate.serde.DefaultSerde(
            durable.QuoteRequest
        )
        assert serde.deserialize(serde.serialize(durable.QuoteRequest(sku="widget"))) == (
            durable.QuoteRequest(sku="widget")
        )


class TestQuoteResponse:

    def test_the_sdk_serde_round_trips_it(self) -> None:
        serde: restate.serde.DefaultSerde[durable.QuoteResponse] = restate.serde.DefaultSerde(
            durable.QuoteResponse
        )
        assert serde.deserialize(serde.serialize(durable.QuoteResponse(cents=250))) == (
            durable.QuoteResponse(cents=250)
        )
