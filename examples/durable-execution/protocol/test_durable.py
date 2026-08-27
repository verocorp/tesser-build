from __future__ import annotations

import pytest

import protocol.durable as durable


class TestWorkflowRequest:

    def test_a_string_field_is_read_from_the_body(self) -> None:
        request = durable.WorkflowRequest(key="o1", body=b'{"sku": "widget", "quantity": 2}')
        assert request.text("sku") == "widget"
        assert request.integer("quantity") == 2

    def test_a_missing_field_is_a_bad_invocation(self) -> None:
        request = durable.WorkflowRequest(key="o1", body=b"{}")
        with pytest.raises(durable.BadInvocation):
            request.text("sku")

    def test_a_bool_is_not_an_integer(self) -> None:
        request = durable.WorkflowRequest(key="o1", body=b'{"quantity": true}')
        with pytest.raises(durable.BadInvocation):
            request.integer("quantity")

    def test_malformed_json_is_a_bad_invocation(self) -> None:
        request = durable.WorkflowRequest(key="o1", body=b"{")
        with pytest.raises(durable.BadInvocation):
            request.text("sku")

    def test_a_non_object_body_is_a_bad_invocation(self) -> None:
        request = durable.WorkflowRequest(key="o1", body=b"[]")
        with pytest.raises(durable.BadInvocation):
            request.text("sku")


class TestActionRequest:

    def test_a_string_field_is_read_from_the_body(self) -> None:
        request = durable.ActionRequest(body=b'{"sku": "widget"}')
        assert request.text("sku") == "widget"

    def test_a_non_object_body_is_a_bad_invocation(self) -> None:
        request = durable.ActionRequest(body=b"[]")
        with pytest.raises(durable.BadInvocation):
            request.text("sku")
