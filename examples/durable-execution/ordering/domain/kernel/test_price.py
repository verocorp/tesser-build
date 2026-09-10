from __future__ import annotations

import pytest

import ordering.domain.kernel as kernel
import tesser.errors as errors


class TestQuantity:

    def test_a_quantity_is_at_least_one_unit(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            kernel.Quantity(0)
        assert excinfo.value.code == "quantity_below_one"

    def test_a_quantity_is_at_most_a_million_units(self) -> None:
        assert int(kernel.Quantity(1_000_000)) == 1_000_000
        with pytest.raises(errors.DomainError) as excinfo:
            kernel.Quantity(1_000_001)
        assert excinfo.value.code == "quantity_above_maximum"


class TestPrice:

    def test_a_price_equals_by_value(self) -> None:
        assert kernel.Price(kernel.PriceSpec(cents=5)) == kernel.Price(kernel.PriceSpec(cents=5))

    def test_a_price_is_never_negative(self) -> None:
        with pytest.raises(errors.DomainError):
            kernel.Price(kernel.PriceSpec(cents=-1))

    def test_a_price_is_at_most_a_trillion_cents(self) -> None:
        kernel.Price(kernel.PriceSpec(cents=10**12))
        with pytest.raises(errors.DomainError) as excinfo:
            kernel.Price(kernel.PriceSpec(cents=10**12 + 1))
        assert excinfo.value.code == "price_above_maximum"

    def test_a_price_times_a_quantity_is_the_total(self) -> None:
        price = kernel.Price(kernel.PriceSpec(cents=250))
        assert price.times(kernel.Quantity(3)) == kernel.Price(kernel.PriceSpec(cents=750))
