from collections.abc import Mapping
from dataclasses import dataclass

from catalog.labels import Labels
from catalog.money import Money, MoneySpec
from catalog.sku import SKU


@dataclass(frozen=True)
class ProductSpec:
    """Primitive leaves and nested specs: Price is a MoneySpec; Labels is a raw
    mapping the Labels constructor will copy."""

    sku: str
    price: MoneySpec
    labels: Mapping[str, str]


class Product:
    """The entity that gives the value objects a domain-meaningful home: the
    system tracks a specific product by its SKU identity. A fact entity — it
    records a price and labels with no lifecycle transition — so equality is
    identity (by SKU) and it exposes no setters. Its ``__eq__`` and ``__hash__``
    are defined together, by SKU.
    """

    def __init__(self, spec: ProductSpec) -> None:
        """Construct from the spec — the single construction path. Each child
        value object validates itself; the constructor adds error context and
        enforces any invariants that span the fields."""
        try:
            self._sku = SKU(spec.sku)
        except ValueError as e:
            raise ValueError(f"invalid sku: {e}") from e
        try:
            self._price = Money.from_spec(spec.price)
        except ValueError as e:
            raise ValueError(f"invalid price: {e}") from e
        self._labels = Labels.new(spec.labels)

    @property
    def sku(self) -> SKU:
        return self._sku

    @property
    def price(self) -> Money:
        return self._price

    @property
    def labels(self) -> Labels:
        return self._labels

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Product) and other._sku == self._sku

    def __hash__(self) -> int:
        return hash(self._sku)
