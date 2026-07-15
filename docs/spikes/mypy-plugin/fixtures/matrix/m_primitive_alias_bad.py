"""Primitive field disguised by a same-module type alias -- should-flag."""
from dataclasses import dataclass

Sku = str  # alias, NOT a distinct nominal type -- still bare str at runtime


@dataclass(frozen=True)
class Product:
    sku: Sku  # disguised primitive -- should-flag (primitive obsession)


p = Product(sku="ABC-1")  # valid construction call
