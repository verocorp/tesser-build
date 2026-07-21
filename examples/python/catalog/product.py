from collections.abc import Mapping
from dataclasses import dataclass

from catalog.labels import Labels
from catalog.money import Money, MoneySpec
from catalog.sku import SKU


@dataclass(frozen=True)
class ProductSpec:

    sku: str
    price: MoneySpec
    labels: Mapping[str, str]


class Product:

    def __init__(self, spec: ProductSpec) -> None:
        try:
            self._sku = SKU(spec.sku)
        except ValueError as e:
            raise ValueError(f"invalid sku: {e}") from e
        try:
            self._price = Money(spec.price)
        except ValueError as e:
            raise ValueError(f"invalid price: {e}") from e
        self._labels = Labels(spec.labels)

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
