"""linkpolicy's own construction config — lives in ``wiring`` (impl), NOT on the
public top level (which is ``Client`` + DTOs only). The toolkit prescribes the
shape (primitive-leaved, context-owned), never the fields; ``storage`` here is
this service's coordinate, an illustration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    storage: str  # the resource coordinate; "memory" for the zero-dependency example
