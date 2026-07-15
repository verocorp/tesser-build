"""Classification-aware checks — the ones that need the stereotype registry.

Unlike the syntactic ``checks._Checker`` (which reads one file's shape), these
key on what a class *is* (``classify.ClassInfo``). DDD010 is the reinstated
``primitiveaccessor`` rule and the load-bearing spec/VO discriminator: a value
object hides its representation, a spec exposes it.
"""

import ast

from ddd_vet.astutil import _annotation_base
from ddd_vet.classify import ClassInfo, Stereotype
from ddd_vet.finding import Finding

# Base names that are raw primitives a value object must not expose as a public
# field. A safe single-representation value (a currency code) may be exposed via
# an accessor, and a multi-representation primitive (Decimal) is wrapped in its
# own VO — but a *public primitive field* on a VO is always a representation leak.
_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    {"str", "int", "float", "bool", "bytes", "complex", "Decimal"}
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
        if info is None or info.stereotype is not Stereotype.VALUE_OBJECT:
            continue
        # DDD010 — a value object must not expose a public primitive field.
        for member in stmt.body:
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
                        f"value object {stmt.name!r} exposes a public primitive field "
                        f"{field!r}; hide the representation (underscore-private) — a "
                        "value object's primitive must not leak",
                    )
                )
    return findings
