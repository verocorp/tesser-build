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

from tessercheck.astutil import _annotation_base, _name_of
from tessercheck.classify import ClassInfo, Stereotype
from tessercheck.finding import Finding

# A predicate over 1-based line numbers: is a ``# tessercheck:ignore`` on that line?
_Suppressed = Callable[[int], bool]

# The scalar representations a value object wraps — "primitive" in the DDD
# (primitive-obsession) sense, so the stdlib temporals count, not only the
# language builtins. ONE set answers two faces of the same question: which
# scalars a leaf value object wraps, and which a domain type must not hand out
# raw (the TB010 accessor ban + the TB016 compound-field ban). Every member has
# a canonical exit — this set is exactly _CANONICAL_EXIT's keys — because a
# wrappable scalar is one you can both hide inside a VO AND get a canonical form
# back out of. A currency code is a Currency VO, a Decimal its own VO, a date a
# Day VO; the leaf's conversion exit (serialization.md rule 3) is the door back
# out. What is NOT here: what makes a single-field class structured (a collection
# field, or a field typed as another domain object) — and the NON-wrappable
# scalars below.
_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    {"str", "int", "float", "bytes", "Decimal", "date", "datetime", "time"}
)

# Scalars that are NOT value-object material — a value object may not wrap one
# (maintainer ruling 2026-07-20). ``bool`` is atomic: model it raw, or reach for
# an enum when it is really richer than binary; it has no canonical conversion
# exit (its only candidate dunder, ``__bool__``, is truthiness, not a
# serialization form) and no non-lossy projection onto one that survives every
# wire. ``complex`` has no domain wire form at all. They are still scalars for
# leaf-vs-structured discrimination (a single ``bool`` field is a leaf, not a
# compound) — but the leaf itself is the violation, flagged by TB016.
_NON_WRAPPABLE: frozenset[str] = frozenset({"bool", "complex"})

# Collection bases whose instance a caller can mutate. Handing back the backing
# store of one of these lets a caller ``.append``/``.pop``/``[k]=`` into the
# aggregate's internals without going through a root-guarded transition. A
# ``tuple``/``frozenset``/``Sequence`` accessor is read-only by type and is not
# flagged here (the deeper "immutable container of mutable children" leak is a
# semantic concern the aggregate handles by cloning — e.g. Campaign.links).
_MUTABLE_COLLECTION_BASES: frozenset[str] = frozenset(
    {"list", "List", "dict", "Dict", "set", "Set", "MutableSequence", "MutableMapping"}
)

# The decorators that make a method a *type-level* factory — a construction path
# reachable without an instance. Both are doors: a staticmethod returning the own
# type is the same second constructor as a classmethod, just spelled without cls.
_FACTORY_DECORATORS: frozenset[str] = frozenset({"classmethod", "staticmethod"})

_SUPPRESS_MARKER = "# tessercheck:ignore"

# The conversion protocol — the only sanctioned primitive doors out of a leaf
# value object (serialization.md rule 3). A leaf defines exactly the one
# matching its backing type; a structured type defines none (rule 5).
_CONVERSION_DUNDERS: frozenset[str] = frozenset(
    {"__str__", "__int__", "__float__", "__bytes__"}
)

# Every wrappable primitive's ruled canonical exit — keys are exactly
# _PRIMITIVE_TYPES (a wrappable scalar is by definition one with a canonical form
# out). The four native primitives map to their own conversion protocol; the
# representations without one (Decimal, date, datetime, time) exit as canonical
# text via __str__ under the pinned policies (serialization.md rule 3). bool and
# complex are absent because they are not wrappable at all (_NON_WRAPPABLE) — not
# because they are wrappable-without-an-exit.
_CANONICAL_EXIT: dict[str, str] = {
    "str": "__str__",
    "int": "__int__",
    "float": "__float__",
    "bytes": "__bytes__",
    "Decimal": "__str__",
    "date": "__str__",
    "datetime": "__str__",
    "time": "__str__",
}

# Backing type -> the canonical-form policy helper its exit must delegate to
# (serialization.md rule 3). Each policy gets exactly ONE implementation site, so
# a consumer's tenth datetime value object cannot drift from the pinned format,
# and every canonical exit announces itself at its definition (grep ``canonical_``
# finds them all; a hand-rolled __str__ is visibly not one).
#
# A PROPER SUBSET of _CANONICAL_EXIT, and the gap is honest: ``date`` and ``time``
# have a ruled exit (__str__, from the 2026-07-20 temporal ruling) but no ruled
# canonical FORM yet — the time-type taxonomy is a named open decision (TODOS.md).
# Their leaves are out of contract here rather than guessed at, exactly as UUID
# and Enum are out of contract for stereotype classification. Rule the taxonomy
# and this map grows to match _CANONICAL_EXIT's keys.
_CANONICAL_HELPER: dict[str, str] = {
    "str": "canonical_str",
    "int": "canonical_int",
    "float": "canonical_float",
    "bytes": "canonical_bytes",
    "Decimal": "canonical_decimal",
    "datetime": "canonical_datetime",
}


def _fields(node: ast.ClassDef) -> list[ast.AnnAssign]:
    """The class's annotated fields, in declaration order (ClassVars excluded —
    they are not instance state)."""
    return [
        m
        for m in node.body
        if isinstance(m, ast.AnnAssign)
        and isinstance(m.target, ast.Name)
        and _annotation_base(m.annotation) != "ClassVar"
    ]


def _leaf_backing(node: ast.ClassDef) -> str | None:
    """The backing scalar of a *leaf* value object, or ``None`` if the class is
    structured.

    A leaf is the mechanically crisp case: exactly one field, annotated with a
    bare scalar name. Anything else — two or more fields (a compound), a
    collection field (a collection value object), a field typed as another
    domain object — is structured, and structured types have no primitive exit
    at all. This is the discriminator the norm's "a leaf has exactly one
    matching conversion dunder; a structured type has none" contract rests on.

    Membership is keyed on every scalar — wrappable (:data:`_PRIMITIVE_TYPES`)
    OR not (:data:`_NON_WRAPPABLE`) — because leaf-vs-structured is a structural
    question: a single ``bool`` field is a leaf shape, not a compound. Whether a
    ``bool`` leaf is *allowed* is a separate matter TB016 owns; keeping it a leaf
    here stops it being misreported as a structured type with an illegal dunder.
    """
    fields = _fields(node)
    if len(fields) != 1:
        return None
    base = _annotation_base(fields[0].annotation)
    return base if base in (_PRIMITIVE_TYPES | _NON_WRAPPABLE) else None


def _defined_conversion_dunders(node: ast.ClassDef) -> list[ast.FunctionDef]:
    return [
        m
        for m in node.body
        if isinstance(m, ast.FunctionDef) and m.name in _CONVERSION_DUNDERS
    ]


def _annotation_names(ann: ast.expr | None) -> set[str]:
    """Every type name anywhere in an annotation, string forward references
    resolved. ``"Slug"``, ``Slug | None`` and ``Optional["Slug"]`` all yield
    ``Slug`` — a wrapper is not an escape hatch, and a quoted annotation is the
    ordinary way to name your own class before it exists."""
    if ann is None:
        return set()
    names: set[str] = set()
    for sub in ast.walk(ann):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            try:
                names |= _annotation_names(ast.parse(sub.value, mode="eval").body)
            except SyntaxError:
                names.add(sub.value)
    return names


def _decorator_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        name
        for dec in fn.decorator_list
        if (name := _name_of(dec.func if isinstance(dec, ast.Call) else dec)) is not None
    }


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
        if info.stereotype in (Stereotype.VALUE_OBJECT, Stereotype.IDENTITY_OBJECT):
            # The serialization norm governs every domain data type: how its
            # primitives leave (TB015) and, for value objects, what it holds
            # inside (TB016).
            findings.extend(_check_public_decompiler(stmt, registry, path, suppressed))
        if info.stereotype is Stereotype.VALUE_OBJECT:
            findings.extend(_check_vo_exposure(stmt, path, suppressed))
            findings.extend(_check_compound_raw_primitive(stmt, path, suppressed))
            findings.extend(_check_single_door(stmt, path, suppressed))
            findings.extend(_check_canonical_routing(stmt, path, suppressed))
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
    unexported). Value objects are handled by TB017
    (:func:`_check_single_door`), which is the *stricter* rule: any own-type
    factory, not just the ``from_spec`` name. The asymmetry is deliberate and
    is about migration cost, not principle — see below.

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


def _check_single_door(
    node: ast.ClassDef,
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB018's sibling on the inbound side — TB017: a value object has ONE
    construction door, its own ``__init__``.

    A compound takes its spec; a leaf takes its canonical form and converts
    inside; a collection value object takes the collection. Any
    ``classmethod``/``staticmethod`` returning the own type is a *second* door,
    and the name it goes by does not soften it: ``from_spec`` and ``parse`` are
    the accreted-second-constructor smell, ``new``/``require`` the ergonomic
    factory pair. The 2026-07-20 ruling swept all of them in uniformly, and the
    collection value object — the shape the carve-out would have been for — is
    the case that settled it: ``new`` (permissive) and ``require`` (non-empty)
    enforce *different invariants on one type*, so what the type guarantees
    depends on which door the caller picked. That is a stronger version of the
    defect the one-door rule exists to prevent, not an exception to it.

    Scoped to value objects. Entities and aggregates keep :func:`_check_construction`
    (TB013), which is deliberately narrower — it flags the ``from_spec`` name
    only, because the positive rule would fire on every not-yet-migrated entity.
    A factory returning something *other* than the own type is not a door and is
    left alone.
    """
    findings: list[Finding] = []
    for member in node.body:
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not (_decorator_names(member) & _FACTORY_DECORATORS):
            continue
        returned = _annotation_names(member.returns)
        if not ({node.name, "Self"} & returned):
            continue
        if suppressed(member.lineno):
            continue
        findings.append(
            Finding(
                path,
                member.lineno,
                member.col_offset + 1,
                "TB017",
                f"value object {node.name!r} defines a second construction door "
                f"{member.name!r}; a value object constructs through its own "
                "__init__ and nothing else — a compound takes its spec, a leaf "
                "its canonical form, a collection the collection. Two doors let "
                "two callers build the same type under different invariants",
            )
        )
    return findings


def _check_public_decompiler(
    node: ast.ClassDef,
    registry: dict[str, ClassInfo],
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB015 — a domain object never serializes itself, and its primitives leave
    through exactly one door per shape (serialization.md rules 1, 3 and 5).

    Four shapes, one code:

    1. **spec-return** — a public method whose return type is a spec-classified
       class. That is the outbound decompose surface rule 1 bans; the spec is
       inbound-only, and the sanctioned outbound walk is the application layer's
       parts module.
    2. **emit-a-sink** — a public method returning ``None`` that hands a private
       field to one of its own parameters. Streaming the representation out is
       the same leak wearing a callback.
    3. **mismatched or second exit on a leaf** — a leaf defines exactly the one
       conversion dunder matching its backing type. A second dunder is a second
       door; a mismatched one (a str-backed value object with ``__int__``) is a
       disguise.
    4. **any conversion dunder on a structured type** — compounds, entities and
       aggregates decompose structurally and have no primitive exit at all. The
       zero-dunder contract has no debug carve-out (2026-07-20 ruling); ``repr``
       is the debug surface.

    Deeper laundering — building a dict through locals, delegating to a private
    helper — is declared out of contract and stays review territory.
    """
    findings: list[Finding] = []

    def flag(at: ast.AST, message: str) -> None:
        line = getattr(at, "lineno", node.lineno)
        col = getattr(at, "col_offset", node.col_offset)
        if not suppressed(line):
            findings.append(Finding(path, line, col + 1, "TB015", message))

    for member in node.body:
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if member.name.startswith("_"):
            continue
        returned = _annotation_base(member.returns) if member.returns is not None else None
        target = registry.get(returned or "")
        if target is not None and target.stereotype is Stereotype.SPEC:
            flag(
                member,
                f"{node.name}.{member.name} returns the spec {returned!r} — a "
                "public decompose-to-primitives surface. The spec is inbound-only; "
                "the outbound walk belongs to the application layer's parts module",
            )
        elif returned in (None, "None") and _emits_private_field(member):
            flag(
                member,
                f"{node.name}.{member.name} streams private fields into a sink — "
                "a decompose surface wearing a callback. Edges consume the parts "
                "record; the domain exports no shape",
            )

    dunders = _defined_conversion_dunders(node)
    if not dunders:
        return findings

    backing = _leaf_backing(node)
    if node.name in registry and registry[node.name].stereotype is Stereotype.IDENTITY_OBJECT:
        backing = None

    if backing is None:
        for fn in dunders:
            flag(
                fn,
                f"{node.name} is a structured domain object and defines {fn.name} — "
                "compounds, entities and aggregates have no primitive exit at all. "
                "They decompose structurally through value-object accessors; repr "
                "is the debug surface",
            )
        return findings

    expected = _CANONICAL_EXIT.get(backing)
    if expected is None:
        # A leaf backed by a scalar the norm has not ruled (``date``): it IS a
        # leaf, so it is not the structured-type violation above, but its exit
        # has no ruled shape to check against — out of contract, left alone.
        return findings

    for fn in dunders:
        if fn.name != expected:
            flag(
                fn,
                f"{node.name} is backed by {backing} and defines {fn.name}; its one "
                f"canonical exit is {expected}. A second door lets two "
                "representations of the same value diverge, and a mismatched one "
                "is a disguise",
            )
    return findings


def _delegated_call_name(fn: ast.FunctionDef) -> str | None:
    """The name of the function a one-line ``return f(...)`` body delegates to,
    or ``None`` when the body is anything else.

    Deliberately strict about *bare* delegation: ``return canonical_str(x).upper()``
    returns ``None`` (the outer call is the attribute, not the helper), because a
    post-processed helper result is no longer the policy's output — the exit has
    quietly acquired a second author.
    """
    if len(fn.body) != 1:
        return None
    stmt = fn.body[0]
    if not isinstance(stmt, ast.Return) or not isinstance(stmt.value, ast.Call):
        return None
    return stmt.value.func.id if isinstance(stmt.value.func, ast.Name) else None


def _check_canonical_routing(
    node: ast.ClassDef,
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB018 — a leaf value object's conversion exit delegates to the
    ``canonical_*`` policy helper for its backing type, in one line.

    Rule 3 pins each canonical form once (``Decimal`` as a scientific string,
    ``datetime`` as UTC-normalized ISO-8601 at microsecond precision) and routes
    every exit through that single implementation. A hand-rolled
    ``return self._value`` or ``return str(self._value)`` is a *second*
    implementation of the same canonical form: it is correct on the day it is
    written and drifts the day the policy changes, silently, because nothing
    connects it to the policy. Changing a canonical form is a breaking change,
    and it can only be made in one place if there IS one place.

    Two shapes under one code: not a delegation at all, and delegation to the
    wrong policy (a ``Decimal`` leaf exiting through ``canonical_str`` gets str's
    identity instead of the pinned decimal text).

    The *mismatched dunder* shape belongs to TB015, so a dunder that is not this
    backing type's ruled exit is skipped here — one violation, one code.
    """
    backing = _leaf_backing(node)
    if backing is None:
        return []
    helper = _CANONICAL_HELPER.get(backing)
    if helper is None:
        return []

    findings: list[Finding] = []
    for fn in _defined_conversion_dunders(node):
        if fn.name != _CANONICAL_EXIT.get(backing):
            continue
        called = _delegated_call_name(fn)
        if called == helper or suppressed(fn.lineno):
            continue
        if called is not None and called.startswith("canonical_"):
            detail = (
                f"delegates to {called} but is backed by {backing}; its canonical "
                f"form is {helper}'s. Routing through another type's policy "
                "produces a form nothing else in the system agrees on"
            )
        else:
            detail = (
                f"hand-rolls its canonical form; delegate to {helper} in one line "
                f"(return {helper}(self._value)). A hand-rolled exit is a second "
                "implementation of a pinned form — correct today, silently "
                "drifted the day the policy changes"
            )
        findings.append(
            Finding(
                path,
                fn.lineno,
                fn.col_offset + 1,
                "TB018",
                f"value object {node.name!r} exit {fn.name} {detail}",
            )
        )
    return findings


def _emits_private_field(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when ``fn`` passes one of ``self``'s private fields as an argument to
    a call on one of its own parameters — the emit-a-sink shape.

    Scoped deliberately tight: the sink must be a declared parameter, so an
    ordinary method that happens to call a helper with its own state is not
    swept in. Laundering through a local is out of contract.
    """
    params = {a.arg for a in fn.args.args[1:]} | {a.arg for a in fn.args.kwonlyargs}
    if not params:
        return False
    for call in ast.walk(fn):
        if not isinstance(call, ast.Call):
            continue
        receiver = call.func
        if isinstance(receiver, ast.Attribute):
            receiver = receiver.value
        if not (isinstance(receiver, ast.Name) and receiver.id in params):
            continue
        for arg in call.args:
            for sub in ast.walk(arg):
                if (
                    isinstance(sub, ast.Attribute)
                    and sub.attr.startswith("_")
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id == "self"
                ):
                    return True
    return False


def _check_compound_raw_primitive(
    node: ast.ClassDef,
    path: str,
    suppressed: "_Suppressed",
) -> list[Finding]:
    """TB016 — what a value object may be built from (serialization.md rule 5's
    internal half; the 2026-07-20 R1 ruling and its bool/complex amendment).

    Two violations, one code:

    * **A bool/complex leaf.** ``bool`` and ``complex`` are not value-object
      material: a ``bool`` is atomic (model it raw, or an enum when it is richer
      than binary) and has no canonical conversion exit; ``complex`` has no
      domain wire form. A value object that wraps one is the violation itself,
      regardless of field count.
    * **A compound holding a bare primitive.** A value object with two or more
      fields is a compound — a concept assembled from other concepts, each of
      them a value object (``Money{MoneyAmount, MoneyCurrency}``, not
      ``Money{Decimal, str}``). A bare wrappable primitive in a compound strands
      its validation and behavior at the compound (the quanta ``Decimal``
      precedent) and leaves the component with no canonical exit of its own.

    A single-field value object wrapping one wrappable primitive is a leaf and is
    untouched: that is exactly what a leaf is for.
    """
    findings: list[Finding] = []
    fields = _fields(node)

    for field in fields:
        if _annotation_base(field.annotation) not in _NON_WRAPPABLE:
            continue
        if suppressed(field.lineno):
            continue
        name = field.target.id if isinstance(field.target, ast.Name) else "?"
        base = _annotation_base(field.annotation)
        findings.append(
            Finding(
                path,
                field.lineno,
                field.col_offset + 1,
                "TB016",
                f"{node.name}.{name} is a {base}; {base} is not value-object "
                "material — a bool is atomic (model it raw, or an enum), complex "
                "has no domain wire form. Do not wrap it in a value object",
            )
        )

    if len(fields) < 2:
        return findings
    for field in fields:
        if not _contains_primitive(field.annotation):
            continue
        if suppressed(field.lineno):
            continue
        name = field.target.id if isinstance(field.target, ast.Name) else "?"
        findings.append(
            Finding(
                path,
                field.lineno,
                field.col_offset + 1,
                "TB016",
                f"{node.name}.{name} is a bare primitive in a compound value "
                "object; components are value objects — give it its own type so "
                "its validation, behavior and canonical exit live with it",
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
