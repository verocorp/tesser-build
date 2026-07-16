"""Classification-aware checks — the ones that need the stereotype registry.

Unlike the syntactic ``checks._Checker`` (which reads one file's shape), these
key on what a class *is* (``classify.ClassInfo``):

* **DDD010** (value objects) — the reinstated ``primitiveaccessor`` and the
  load-bearing spec/VO discriminator: a value object hides its representation, a
  spec exposes it.
* **DDD011** (identity objects) — the aggregate/entity defensive-copy rule: an
  accessor must not hand back its backing mutable collection; return a copy so a
  caller cannot mutate the aggregate's internals behind the root's back.
"""

import ast
from typing import Callable

from ddd_vet.astutil import _annotation_base
from ddd_vet.classify import ClassInfo, Stereotype
from ddd_vet.finding import Finding

# A predicate over 1-based line numbers: is a ``# ddd:ignore`` on that line?
_Suppressed = Callable[[int], bool]

# Base names that are raw primitives a value object must not expose as a public
# field. A safe single-representation value (a currency code) may be exposed via
# an accessor, and a multi-representation primitive (Decimal) is wrapped in its
# own VO — but a *public primitive field* on a VO is always a representation leak.
_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    {"str", "int", "float", "bool", "bytes", "complex", "Decimal"}
)

# Collection bases whose instance a caller can mutate. Handing back the backing
# store of one of these lets a caller ``.append``/``.pop``/``[k]=`` into the
# aggregate's internals without going through a root-guarded transition. A
# ``tuple``/``frozenset``/``Sequence`` accessor is read-only by type and is not
# flagged here (the deeper "immutable container of mutable children" leak is a
# semantic concern the aggregate handles by cloning — e.g. Campaign.links).
_MUTABLE_COLLECTION_BASES: frozenset[str] = frozenset(
    {"list", "List", "dict", "Dict", "set", "Set", "MutableSequence", "MutableMapping"}
)

_SUPPRESS_MARKER = "# ddd:ignore"


def check_typed(
    registry: dict[str, ClassInfo], path: str, tree: ast.Module, source: str
) -> list[Finding]:
    """Every classification-aware finding for one file."""
    lines = source.splitlines()

    def suppressed(line: int) -> bool:
        return 1 <= line <= len(lines) and _SUPPRESS_MARKER in lines[line - 1]

    findings: list[Finding] = []
    for stmt in tree.body:
        if not isinstance(stmt, ast.ClassDef):
            continue
        info = registry.get(stmt.name)
        if info is None:
            continue
        if info.stereotype is Stereotype.VALUE_OBJECT:
            findings.extend(_check_vo_exposure(stmt, path, suppressed))
        elif info.stereotype is Stereotype.IDENTITY_OBJECT:
            findings.extend(_check_collection_leak(stmt, path, suppressed))
    return findings


def _check_vo_exposure(
    node: ast.ClassDef, path: str, suppressed: "_Suppressed"
) -> list[Finding]:
    """DDD010 — a value object must not expose a public primitive field."""
    findings: list[Finding] = []
    for member in node.body:
        if not (isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name)):
            continue
        field = member.target.id
        if field.startswith("_"):
            continue
        if _annotation_base(member.annotation) in _PRIMITIVE_TYPES:
            if suppressed(member.lineno):
                continue
            findings.append(
                Finding(
                    path,
                    member.lineno,
                    member.col_offset + 1,
                    "DDD010",
                    f"value object {node.name!r} exposes a public primitive field "
                    f"{field!r}; hide the representation (underscore-private) — a "
                    "value object's primitive must not leak",
                )
            )
    return findings


def _check_collection_leak(
    node: ast.ClassDef, path: str, suppressed: "_Suppressed"
) -> list[Finding]:
    """DDD011 — an aggregate/entity accessor must not return its backing mutable
    collection directly; return a defensive copy instead."""
    findings: list[Finding] = []
    for member in node.body:
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ann = member.returns
        if ann is None or _annotation_base(ann) not in _MUTABLE_COLLECTION_BASES:
            continue
        leaked = _bare_self_field_returned(member)
        if leaked is None or suppressed(member.lineno):
            continue
        findings.append(
            Finding(
                path,
                member.lineno,
                member.col_offset + 1,
                "DDD011",
                f"{node.name!r}.{member.name} returns its backing collection "
                f"{leaked!r} directly; a caller can mutate the aggregate's "
                "internals behind the root — return a defensive copy "
                f"(e.g. list(self.{leaked}) / dict(self.{leaked}))",
            )
        )
    return findings


def _bare_self_field_returned(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """The attribute name if ``fn``'s body is exactly ``return self._x`` (past an
    optional docstring); ``None`` if it wraps, copies, or does anything else.

    ``return self._items`` leaks the backing store; ``return list(self._items)``
    or ``return tuple(...)`` is a Call, not a bare Attribute, and is clean.
    """
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # skip a docstring
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None
    value = body[0].value
    if (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "self"
    ):
        return value.attr
    return None
