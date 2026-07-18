"""reports' own construction config — lives in ``wiring`` (impl), NOT on the
public top level, same as every sibling. reports holds no resources today, so
the spec is empty; it exists so construction stays uniform across contexts and
a real coordinate (e.g. a read-model cache DSN) lands HERE, not on the public
seam and not as a bootstrap special case.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    pass
