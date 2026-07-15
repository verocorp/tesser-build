"""Primitive field disguised by a cross-module import alias -- should-flag."""
from dataclasses import dataclass

from otherpkg.types import CustomerId  # = str, defined in another module


@dataclass(frozen=True)
class Customer:
    id: CustomerId  # disguised primitive, resolved across a module boundary


c = Customer(id="cust-1")  # valid construction call
