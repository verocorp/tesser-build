"""campaign's own construction config — lives in ``wiring`` (impl), NOT on the
public top level. Shape is toolkit-prescribed (primitive-leaved, context-owned);
the field is this service's own coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    storage: str  # the resource coordinate; "memory" for the zero-dependency example
