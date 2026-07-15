"""Primitive wrapped in NewType -- a distinct nominal type, not the primitive
itself, so it is NOT primitive obsession -- expected verdict: should-pass."""
from dataclasses import dataclass
from typing import NewType

Quantity = NewType("Quantity", int)


@dataclass(frozen=True)
class Order:
    quantity: Quantity  # NewType wrapper -- should-pass (nominal, not bare int)


o = Order(quantity=Quantity(5))  # valid construction call
