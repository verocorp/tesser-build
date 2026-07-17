"""ddd-vet-py — the Python analog of go-ddd's ``ddd-vet``.

A zero-dependency, stdlib-``ast`` conformance analyzer for the DDD construction
conventions taught in ``skills/ddd/python.md``. It enforces the *syntactically
decidable* subset on the frozen-dataclass substrate the skill teaches; the
type-aware residuals (primitive-obsession field resolution, identity-``__eq__``
fields) are a deferred P1 mypy-plugin decision, not part of v1.

Run it: ``python -m ddd_vet <paths>`` (exit 1 on any finding).
"""

from ddd_vet.finding import CHECKS, CheckMeta, Finding
from ddd_vet.run import run_paths, run_source

__all__ = ["CHECKS", "CheckMeta", "Finding", "run_paths", "run_source"]

__version__ = "0.1.0"
