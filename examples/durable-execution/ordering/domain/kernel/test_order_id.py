from __future__ import annotations

import pytest

import ordering.domain.kernel as kernel
import tesser.errors as errors


class TestOrderId:

    def test_an_order_id_is_never_empty(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            kernel.OrderId("")
        assert excinfo.value.code == "empty_order_id"

    def test_an_order_id_is_never_a_dot_segment(self) -> None:
        for value in (".", ".."):
            with pytest.raises(errors.DomainError) as excinfo:
                kernel.OrderId(value)
            assert excinfo.value.code == "dotted_order_id"
        assert str(kernel.OrderId("..x")) == "..x"

    def test_an_order_id_equals_by_value(self) -> None:
        assert kernel.OrderId("o1") == kernel.OrderId("o1")
        assert kernel.OrderId("o1") != kernel.OrderId("o2")
