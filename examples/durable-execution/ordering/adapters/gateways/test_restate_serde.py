from __future__ import annotations

import json

import ordering.adapters.gateways.restate_serde as restate_serde
import ordering.application.ports.order_workflow as order_workflow


class TestRecordSerde:

    def test_it_round_trips_a_record_through_json(self) -> None:
        serde = restate_serde.RecordSerde(order_workflow.StartRequest)
        raw = serde.serialize(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))
        assert json.loads(raw) == {"order_id": "o1", "sku": "widget", "quantity": 2}
        back = serde.deserialize(raw)
        assert back is not None
        assert vars(back) == {"order_id": "o1", "sku": "widget", "quantity": 2}

    def test_an_empty_body_is_no_record(self) -> None:
        serde = restate_serde.RecordSerde(order_workflow.StartResponse)
        assert serde.serialize(None) == b""
        assert serde.deserialize(b"") is None
