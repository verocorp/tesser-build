from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class RunRequest:
    sku: str
    quantity: int


@dataclasses.dataclass(frozen=True)
class RunResponse:
    order_id: str
    total_cents: int


@dataclasses.dataclass(frozen=True)
class QuoteRequest:
    sku: str


@dataclasses.dataclass(frozen=True)
class QuoteResponse:
    cents: int
