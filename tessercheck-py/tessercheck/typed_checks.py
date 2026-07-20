"""Classification-aware checks — the ones that need the stereotype registry.

Unlike the syntactic ``checks._Checker`` (which reads one file's shape), these
key on what a class *is* (``classify.ClassInfo``):

* **TB010** (value objects) — the reinstated ``primitiveaccessor`` and the
  load-bearing spec/VO discriminator: a value object hides its representation, a
  spec exposes it. Both leak shapes are flagged: the public primitive field and
  the passthrough accessor returning the raw primitive (maintainer ruling
  2026-07-19; the design doc's earlier "safe single-representation accessor"
  allowance is closed — accessors return value objects).
* **TB011** (identity objects) — the aggregate/entity defensive-copy rule: an
  accessor must not hand back its backing mutable collection; return a copy so a
  caller cannot mutate the aggregate's internals behind the root's back.
* **TB012** (identity objects) — the aggregate boundary rule: reference another
  aggregate root by its ID value object, never by holding the root object across
  the boundary. Needs the whole-tree registry (``run_paths``) to know a held
  field's type is itself a root.
* **TB013** (identity objects) — construct through the spec: ``__init__(self,
  spec)`` is the single construction path; no separate ``from_spec`` factory and
  no value-taking constructor. Value objects are exempt (compound-VO
  construction is a separate, unsettled question).
* **TB014** (value objects + identity objects) — equality must match the
  stereotype: a value object compares by value; an entity defines ``__eq__`` and
  ``__hash__`` together (by ID); an aggregate root blocks accidental equality
  (``__eq__ = None`` / ``__hash__ = None``). The check the classifier was built to
  enable — equality is what *defines* each domain type.
"""

import ast
from typing import Callable

from tessercheck.astutil import _annotation_base
from tessercheck.classify import ClassInfo, Stereotype
from tessercheck.finding import Finding

# A predicate over 1-based line numbers: is a ``# tessercheck:ignore`` on that line?
_Suppressed = Callable[[int], bool]

# Base names that are raw primitives a value object must not expose — neither
# as a public field nor through a passthrough accessor (the 2026-07-19 ruling
# closed the earlier "safe single-representation accessor" allowance: a
# currency code is a Currency VO). A multi-representation primitive (Decimal)
# is likewise wrapped in its own VO; a leaf's canonical conversion exit
# (2026-07-20 ruling: the ONE dunder matching its backing primitive —
# skills/tesser-build/serialization.md rule 3) is the sole primitive door.
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

_SUPPRESS_MARKER = "# tessercheck:ignore"


def _contains_primitive(ann: ast.expr | None) -> bool:
    """True when any name anywhere in the annotation is a banned primitive —
    so ``str | None``, ``Optional[str]``, and a container of primitives all
    count, not just a bare ``str`` (a union wrapper is not an escape hatch)."""
    if ann is None:
        return False
    for sub in ast.walk(ann):
        if isinstance(sub, ast.Name):
            name: str | None = sub.id
        elif isinstance(sub, ast.Attribute):
            name = sub.attr
        else:
            continue
        if name in _PRIMITIVE_TYPES:
            return True
    return False


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
        if info.stereotype in (Stereotype.VALUE_OBJECT, Stereotype.IDENTITY_OBJECT):
            # Equality is the defining property of every domain type — the check
            # the classifier was built to enable (see design §5).
            findings.extend(_check_equality(stmt, info, path, suppressed))
        if info.stereotype is Stereotype.VALUE_OBJECT:
            findings.extend(_check_vo_exposure(stmt, path, suppressed))
        elif info.stereotype is Stereotype.IDENTITY_OBJECT:
            findings.extend(_check_collection_leak(stmt, path, suppressed))
            findings.extend(_check_root_by_object(stmt, registry, path, suppressed))
            findings.extend(_check_construction(stmt, path, suppressed))
    return findings


def _check_vo_exposure(
    node: ast.ClassDef, path: str, suppressed: "_Suppressed"
) -> list[Finding]:
    """TB010 — a value object's primitive must not escape: neither as a public
    primitive field nor through a passthrough accessor that hands the raw
    value back (``@property def x(self) -> str: return self._x`` is the same
    leak as ``x: str`` — the rename alone enforces nothing). Components are
    exposed as value objects; a leaf's canonical conversion exit is the sole
    primitive door (serialization.md rule 3), consumed by the parts layer."""
    field_annotations: dict[str, ast.expr] = {}
    for member in node.body:
        if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
            field_annotations[member.target.id] = member.annotation

    findings: list[Finding] = []
    for member in node.body:
        if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
            field = member.target.id
            if field.startswith("_"):
                continue
            if _contains_primitive(member.annotation):
                if suppressed(member.lineno):
                    continue
                findings.append(
                    Finding(
                        path,
                        member.lineno,
                        member.col_offset + 1,
                        "TB010",
                        f"value object {node.name!r} exposes a public primitive field "
                        f"{field!r}; hide the representation (underscore-private) — a "
                        "value object's primitive must not leak",
                    )
                )
        elif isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Underscore-private helpers are internal plumbing, matching the
            # field check's own underscore exemption above; the ban is on the
            # PUBLIC read surface. Dunders (__str__ et al.) are the sanctioned
            # exits.
            if member.name.startswith("_"):
                continue
            returned = _bare_self_field_returned(member)
            if returned is None:
                continue
            primitive = _contains_primitive(member.returns) or _contains_primitive(
                field_annotations.get(returned)
            )
            if not primitive or suppressed(member.lineno):
                continue
            findings.append(
                Finding(
                    path,
                    member.lineno,
                    member.col_offset + 1,
                    "TB010",
                    f"value object {node.name!r} accessor {member.name!r} returns "
                    f"its raw primitive ({returned!r}); the primitive must not "
                    "leak through an accessor either — expose a value object "
                    "(wrap the component); a leaf's canonical conversion exit "
                    "is the sole primitive door (serialization.md)",
                )
            )
    return findings


def _check_equality(
    node: ast.ClassDef, info: ClassInfo, path: str, suppressed: "_Suppressed"
) -> list[Finding]:
    """TB014 — equality must match the stereotype.

    * value object → compares by value; it must not *block* equality.
    * entity → identity equality, with ``__eq__`` and ``__hash__`` defined
      *together* (a lone ``__eq__`` silently makes it unhashable).
    * aggregate root → *blocks* accidental equality: ``__eq__ = None`` and
      ``__hash__ = None`` (an aggregate is not a value; comparing two is a bug).
    """
    eq_method, eq_none, hash_method, hash_none = _eq_hash_shape(node)
    findings: list[Finding] = []

    def flag(message: str) -> None:
        if not suppressed(node.lineno):
            findings.append(
                Finding(path, node.lineno, node.col_offset + 1, "TB014", message)
            )

    if info.stereotype is Stereotype.VALUE_OBJECT:
        if eq_none:
            flag(
                f"value object {node.name!r} blocks equality (__eq__ = None); a "
                "value object compares by value — blocking equality is an "
                "aggregate's rule, not a value object's"
            )
    elif info.is_aggregate_root:
        if eq_method and not eq_none:
            flag(
                f"aggregate root {node.name!r} defines __eq__; an aggregate is "
                "not a value — block accidental equality with __eq__ = None and "
                "__hash__ = None"
            )
        elif eq_none and not hash_none:
            flag(
                f"aggregate root {node.name!r} blocks __eq__ but not __hash__; "
                "block both — set __hash__ = None too"
            )
    else:  # entity (identity object that is not an aggregate root)
        if eq_method and not hash_method:
            flag(
                f"entity {node.name!r} defines __eq__ without __hash__; define "
                "them together (identity by ID) — a lone __eq__ makes the entity "
                "unhashable"
            )
    return findings


def _eq_hash_shape(node: ast.ClassDef) -> tuple[bool, bool, bool, bool]:
    """``(eq_method, eq_none, hash_method, hash_none)`` — how the class handles
    ``__eq__``/``__hash__``: a real method definition, or an ``= None`` class-body
    assignment that blocks it."""
    eq_method = eq_none = hash_method = hash_none = False
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if stmt.name == "__eq__":
                eq_method = True
            elif stmt.name == "__hash__":
                hash_method = True
        elif isinstance(stmt, ast.Assign):
            blocked = isinstance(stmt.value, ast.Constant) and stmt.value.value is None
            for tgt in stmt.targets:
                if not (blocked and isinstance(tgt, ast.Name)):
                    continue
                if tgt.id == "__eq__":
                    eq_none = True
                elif tgt.id == "__hash__":
                    hash_none = True
    return eq_method, eq_none, hash_method, hash_none


def _check_collection_leak(
    node: ast.ClassDef, path: str, suppressed: "_Suppressed"
) -> list[Finding]:
    """TB011 — an aggregate/entity accessor must not return its backing mutable
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
                "TB011",
                f"{node.name!r}.{member.name} returns its backing collection "
                f"{leaked!r} directly; a caller can mutate the aggregate's "
                "internals behind the root — return a defensive copy "
                f"(e.g. list(self.{leaked}) / dict(self.{leaked}))",
            )
        )
    return findings


def _check_root_by_object(
    node: ast.ClassDef,
    registry: dict[str, ClassInfo],
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB011's boundary sibling, TB012 — an aggregate/entity must reference
    another aggregate root by its ID, not hold the root object across the
    boundary.

    "Another root" is the settled signal (``ClassInfo.is_aggregate_root``): a
    reference-identity entity that embeds ≥1 *entity*. Holding a member entity —
    an identity object that embeds only value objects, composed below you — is
    legitimate composition and not flagged; holding another *root* is the
    violation. (``is_member`` cannot be the signal: the moment you wrongly hold a
    root, it looks like your own member.)
    """
    findings: list[Finding] = []
    for name, lineno, col in _held_type_refs(node):
        held = registry.get(name)
        if held is None or not held.is_aggregate_root or name == node.name:
            continue
        if suppressed(lineno):
            continue
        findings.append(
            Finding(
                path,
                lineno,
                col + 1,
                "TB012",
                f"{node.name!r} holds another aggregate root {name!r} by object; "
                f"reference it by its ID value object instead (e.g. {name}ID) — "
                "aggregates cross each other's boundaries by identity, not by "
                "holding the object",
            )
        )
    return findings


def _check_construction(
    node: ast.ClassDef,
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB013 — a structured domain object constructs through its spec.

    The single construction path is ``__init__(self, spec)``: the constructor
    takes the primitive-leaf spec and builds the value objects. There is no
    separate ``from_spec`` factory — that second constructor is ungrounded (Go
    exposes one factory taking the spec, the value-taking construction kept
    unexported). Value objects are exempt (they are not identity objects): the
    compound-VO construction mechanism is a separate, unsettled question.

    Scoped to the ``from_spec`` factory — the exact accreted second constructor.
    The stricter positive rule ("the constructor must *take* the spec, not the
    already-built value objects") is a deliberately deferred extension: it would
    fire broadly on any entity not yet migrated to spec-construction, which is a
    larger, noisier mandate than flagging the redundant factory.
    """
    findings: list[Finding] = []
    for member in node.body:
        if not (isinstance(member, ast.FunctionDef) and member.name == "from_spec"):
            continue
        if suppressed(member.lineno):
            continue
        findings.append(
            Finding(
                path,
                member.lineno,
                member.col_offset + 1,
                "TB013",
                f"{node.name!r} defines a from_spec factory; a structured domain "
                "object constructs through its constructor instead — "
                f"__init__(self, spec: {node.name}Spec) is the single path",
            )
        )
    return findings


def _held_type_refs(node: ast.ClassDef) -> list[tuple[str, int, int]]:
    """Every type name referenced by a field's annotation, with its location.

    Reads both idioms: an entity's ``__init__`` parameter annotations (plain
    classes declare composition there) and class-level ``AnnAssign`` fields
    (dataclass-style). ``list[Warehouse]`` yields both ``list`` and ``Warehouse``
    — the caller resolves each against the registry, so container names simply
    don't match. De-duplicated by (name, line, col).
    """
    refs: list[tuple[str, int, int]] = []
    seen: set[tuple[str, int, int]] = set()

    def collect(annotation: ast.expr) -> None:
        for sub in ast.walk(annotation):
            if isinstance(sub, ast.Name):
                key = (sub.id, sub.lineno, sub.col_offset)
            elif isinstance(sub, ast.Attribute):
                key = (sub.attr, sub.lineno, sub.col_offset)
            else:
                continue
            if key not in seen:
                seen.add(key)
                refs.append(key)

    for member in node.body:
        if isinstance(member, ast.FunctionDef) and member.name == "__init__":
            params = [
                *member.args.posonlyargs,
                *member.args.args,
                *member.args.kwonlyargs,
            ]
            for arg in params:
                if arg.arg != "self" and arg.annotation is not None:
                    collect(arg.annotation)
        elif isinstance(member, ast.AnnAssign):
            collect(member.annotation)
    return refs


def _bare_self_field_returned(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """The attribute name if ``fn`` hands back ``self._x`` unchanged; ``None``
    if it wraps, copies, computes, or does anything else.

    Two shapes match (past an optional docstring): the direct passthrough
    ``return self._x``, and its one-alias disguise ``v = self._x; return v``.
    ``return list(self._items)`` / ``return tuple(...)`` is a Call, not a bare
    Attribute, and is clean. Deeper laundering (conditionals, multiple locals,
    ``or`` fallbacks) is beyond this deliberately syntactic check's depth — the
    norm's teeth are the direct shapes; the rest is code-review territory.
    """
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # skip a docstring

    def self_attr(value: ast.expr | None) -> str | None:
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "self"
        ):
            return value.attr
        return None

    if len(body) == 1 and isinstance(body[0], ast.Return):
        return self_attr(body[0].value)
    if len(body) == 2 and isinstance(body[1], ast.Return) and isinstance(body[1].value, ast.Name):
        first = body[0]
        if (
            isinstance(first, ast.Assign)
            and len(first.targets) == 1
            and isinstance(first.targets[0], ast.Name)
            and body[1].value.id == first.targets[0].id
        ):
            return self_attr(first.value)
        if (
            isinstance(first, ast.AnnAssign)
            and isinstance(first.target, ast.Name)
            and first.value is not None
            and body[1].value.id == first.target.id
        ):
            return self_attr(first.value)
    return None
