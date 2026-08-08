"""Whole-tree stereotype classification — the identity taxonomy.

Two passes over the parsed domain modules
(``docs/design-python-domain-detection.md``):

* **pass 1** classifies each class *locally* by its kind of identity —
  value_object / spec / identity_object / other;
* **pass 2** resolves *embedding* against the pass-1 registry — does an identity
  object own a collection of domain objects (its "aggregate role"), and is it
  composed inside another identity object (a "member")?

Type references resolve by *simple name* against the classifier's own registry
(a bounded context has unique domain-type names), so most of the type-awareness
needs no import resolution and no mypy — the residual disguised cases (alias /
NewType / cross-module) are the optional mypy-plugin's job, not this pass's.
"""

import ast
import os
from dataclasses import dataclass
from enum import Enum

from tessercheck.astutil import (
    _annotation_base,
    _annotation_names,
    _dataclass_frozen,
    _name_of,
)

# The tesser.domain runtime bases, mapped to the stereotype they DECLARE. A
# class that names one of these is not inferred, it is stated: the base is the
# author's answer to the question the local heuristics below are guessing at, so
# it outranks them (see _local_stereotype).
_DECLARED_BASES: dict[str, str] = {
    "ValueObject": "VALUE_OBJECT",
    "Spec": "SPEC",
    "Entity": "IDENTITY_OBJECT",
    "AggregateRoot": "IDENTITY_OBJECT",
    "Aggregate": "IDENTITY_OBJECT",
}

# Annotation bases that denote a *collection of* their element type. Owning a
# collection of domain objects is the structural signal of an aggregate role.
_COLLECTION_BASES: frozenset[str] = frozenset(
    {
        "list", "List", "tuple", "Tuple", "set", "Set", "frozenset", "FrozenSet",
        "Sequence", "MutableSequence", "Iterable", "Collection",
        "dict", "Dict", "Mapping", "MutableMapping",
    }
)


class Stereotype(Enum):
    """The domain-type kinds this analyzer distinguishes.

    ``IDENTITY_OBJECT`` deliberately covers both entity and aggregate root:
    entity-vs-aggregate is a non-distinction *as a type* (an aggregate root is
    an entity in the state of embedding + guarding another entity), so the
    aggregate role is a structural attribute (:attr:`ClassInfo.embeds_entity` /
    :attr:`ClassInfo.is_aggregate_root`), not a separate stereotype.
    """

    VALUE_OBJECT = "value object"
    SPEC = "spec"
    IDENTITY_OBJECT = "identity object"
    OTHER = "other"


@dataclass(frozen=True)
class ClassInfo:
    """The classification of one class, plus the structural facts checks need."""

    name: str
    module: str
    lineno: int
    col: int
    stereotype: Stereotype
    # structural attributes (pass 2)
    embeds_entity: bool  # a field/collection element whose type is an entity
    is_member: bool
    # local signals (pass 1) — retained so checks needn't re-derive them
    frozen_dataclass: bool
    has_post_init: bool
    has_underscore_field: bool
    has_eq_none: bool
    has_eq_method: bool
    field_type_names: frozenset[str]
    collection_element_names: frozenset[str]

    @property
    def is_aggregate_root(self) -> bool:
        """The settled root signal (design §2/§3): a reference-identity entity
        that embeds ≥1 *entity*. Entity-vs-aggregate is not a stereotype — this
        is the sub-state. An entity embedding only value objects is *not* a root.
        """
        return self.stereotype is Stereotype.IDENTITY_OBJECT and self.embeds_entity


def _declared_base_aliases(tree: ast.Module) -> dict[str, str]:
    """Map the names this module can spell a ``tesser.domain`` base with, to the
    stereotype that base declares.

    Both import shapes, aliases included — ``import tesser.domain as ts`` makes
    the base ``ts.ValueObject``; ``from tesser.domain import Entity as E`` makes
    it ``E``. Submodule imports (``from tesser.domain.entity import Entity``)
    count too: ``tesser/domain/__init__.py`` only re-exports them. Mirrors the
    resolution in checks.py, widened past ValueObject to every runtime base.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tesser.domain" or alias.name.startswith("tesser.domain."):
                    prefix = alias.asname or alias.name
                    for base, stereo in _DECLARED_BASES.items():
                        aliases[f"{prefix}.{base}"] = stereo
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "tesser.domain" or mod.startswith("tesser.domain."):
                for alias in node.names:
                    if alias.name in _DECLARED_BASES:
                        aliases[alias.asname or alias.name] = _DECLARED_BASES[alias.name]
    return aliases


def tesser_domain_prefixes(tree: ast.Module) -> frozenset[str]:
    """The attribute prefixes this module can spell a ``tesser.domain`` type
    with — ``{"ts"}`` for ``import tesser.domain as ts``.

    A type reached through one of these is a domain object by DECLARATION, and
    checks may trust it without the defining package being in the analyzed
    tree. tesser-py is a runtime dependency: a consumer analyzing its own app
    never has ``tesser/domain/truth.py`` in scope, and a cross-package domain
    type must not read as foreign just because it lives in the library.
    """
    prefixes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tesser.domain":
                    prefixes.add(alias.asname or alias.name)
    return frozenset(prefixes)


def _dotted_name(node: ast.expr) -> str | None:
    """``ts.ValueObject`` as the string ``"ts.ValueObject"``.

    Not ``_name_of``, which returns only the last segment: matching on the bare
    segment would classify an unrelated local class named ``ValueObject`` as a
    tesser value object.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def _declared_stereotype(node: ast.ClassDef, aliases: dict[str, str]) -> str | None:
    """The stereotype this class DECLARES via a tesser.domain base, if any."""
    for base in node.bases:
        name = _dotted_name(base)
        if name in aliases:
            return aliases[name]
    return None


def _is_property(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if ``fn`` is decorated ``@property`` — a read-only accessor whose
    return type names a field's type."""
    return any(_name_of(dec) == "property" for dec in fn.decorator_list)


def _collection_element_names(ann: ast.expr) -> frozenset[str]:
    """Element type names of a collection annotation (``list[ShortLink]`` ->
    ``{ShortLink}``); empty for a non-collection annotation."""
    if isinstance(ann, ast.Subscript) and _annotation_base(ann.value) in _COLLECTION_BASES:
        return _annotation_names(ann.slice)
    return frozenset()


@dataclass(frozen=True)
class _Scan:
    """Pass-1 local scan of one class, before embedding is resolved."""

    name: str
    module: str
    lineno: int
    col: int
    frozen_dataclass: bool
    any_dataclass: bool
    # The stereotype a tesser.domain base declares outright, if any.
    declared: str | None
    has_method: bool
    has_post_init: bool
    has_underscore_field: bool
    has_eq_none: bool
    has_eq_method: bool
    field_type_names: frozenset[str]
    collection_element_names: frozenset[str]


def _scan_class(
    node: ast.ClassDef, module: str, aliases: dict[str, str] | None = None
) -> _Scan:
    any_dc, frozen, dec = _dataclass_frozen(node.decorator_list)
    methods: set[str] = set()
    has_eq_none = False
    field_types: set[str] = set()
    collection_elems: set[str] = set()
    has_underscore_field = False

    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.add(stmt.name)
            if stmt.name == "__init__":
                # A plain-class entity/aggregate takes its spec here; the spec's
                # own type is not composition, but reading the params is harmless
                # (a spec is not an entity, so it never reads as embedded).
                params = [*stmt.args.posonlyargs, *stmt.args.args, *stmt.args.kwonlyargs]
                for arg in params:
                    if arg.arg == "self" or arg.annotation is None:
                        continue
                    field_types |= _annotation_names(arg.annotation)
                    collection_elems |= _collection_element_names(arg.annotation)
            elif _is_property(stmt) and stmt.returns is not None:
                # A plain-class entity declares its composition through its
                # read-only ``@property`` accessors: the return type of each is a
                # field's type (``links -> tuple[ShortLink, ...]`` embeds
                # ShortLink). This is the reliable signal now that construction
                # takes the spec, not the already-built value objects.
                field_types |= _annotation_names(stmt.returns)
                collection_elems |= _collection_element_names(stmt.returns)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fname = stmt.target.id
            if fname.startswith("_"):
                has_underscore_field = True
            field_types |= _annotation_names(stmt.annotation)
            collection_elems |= _collection_element_names(stmt.annotation)
        elif isinstance(stmt, ast.Assign):
            # ``__eq__ = None`` — the non-comparable identity-object marker.
            for tgt in stmt.targets:
                if (
                    isinstance(tgt, ast.Name)
                    and tgt.id == "__eq__"
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is None
                ):
                    has_eq_none = True

    # A dataclass points DDD reports at the ``@dataclass`` line; a plain class
    # at the ``class`` line.
    anchor: ast.AST = dec if (any_dc and dec is not None) else node
    return _Scan(
        name=node.name,
        module=module,
        lineno=int(getattr(anchor, "lineno", node.lineno)),
        col=int(getattr(anchor, "col_offset", node.col_offset)) + 1,
        frozen_dataclass=frozen,
        any_dataclass=any_dc,
        declared=_declared_stereotype(node, aliases or {}),
        has_method=bool(methods),
        has_post_init="__post_init__" in methods,
        has_underscore_field=has_underscore_field,
        has_eq_none=has_eq_none,
        has_eq_method="__eq__" in methods,
        field_type_names=frozenset(field_types),
        collection_element_names=frozenset(collection_elems),
    )


def _local_stereotype(scan: _Scan) -> Stereotype:
    """Axis 1 — kind of identity, from local signals only.

    A declared tesser.domain base wins outright. The signals below are
    heuristics for an UNdeclared class, and they key on shapes a base-class
    domain object does not have: it is not a dataclass, and it inherits
    ``__eq__`` rather than defining one, so every one of them fell to OTHER —
    invisible to every classifier-keyed check (TB010-TB018).
    """
    if scan.declared is not None:
        return Stereotype[scan.declared]
    if scan.frozen_dataclass:
        # value family: a VO *validates* (__post_init__) and/or *hides* its
        # representation (an underscore-private field). A record / spec / DTO
        # does neither — it is an inert public-field carrier, even if it has a
        # formatting method (a bare method is not enough to make it a VO).
        if scan.has_post_init or scan.has_underscore_field:
            return Stereotype.VALUE_OBJECT
        return Stereotype.SPEC
    if not scan.any_dataclass and (scan.has_eq_method or scan.has_eq_none):
        # identity equality (by id) or blocked equality (``__eq__ = None``).
        return Stereotype.IDENTITY_OBJECT
    return Stereotype.OTHER


def classify_trees(trees: dict[str, ast.Module]) -> dict[str, ClassInfo]:
    """Classify every top-level class across pre-parsed ``{module: tree}``.

    Returns a registry keyed by simple class name.
    """
    scans: dict[str, _Scan] = {}
    stereos: dict[str, Stereotype] = {}
    for module, tree in trees.items():
        aliases = _declared_base_aliases(tree)
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef):
                scan = _scan_class(stmt, module, aliases)
                scans[scan.name] = scan
                stereos[scan.name] = _local_stereotype(scan)

    registry: dict[str, ClassInfo] = {}
    for name, scan in scans.items():
        stereo = stereos[name]
        # The settled root signal: does this class embed ≥1 *entity*? A field or
        # collection element whose type is an identity object. (VOs among the
        # field types don't count — an entity embedding only VOs is an Entity,
        # not an aggregate root.)
        embeds_entity = any(
            stereos.get(t) is Stereotype.IDENTITY_OBJECT for t in scan.field_type_names
        )
        is_member = any(
            name in other.field_type_names
            for other_name, other in scans.items()
            if other_name != name and stereos[other_name] is Stereotype.IDENTITY_OBJECT
        )
        registry[name] = ClassInfo(
            name=name,
            module=scan.module,
            lineno=scan.lineno,
            col=scan.col,
            stereotype=stereo,
            embeds_entity=embeds_entity,
            is_member=is_member,
            frozen_dataclass=scan.frozen_dataclass,
            has_post_init=scan.has_post_init,
            has_underscore_field=scan.has_underscore_field,
            has_eq_none=scan.has_eq_none,
            has_eq_method=scan.has_eq_method,
            field_type_names=scan.field_type_names,
            collection_element_names=scan.collection_element_names,
        )
    return registry


def classify_sources(sources: dict[str, str]) -> dict[str, ClassInfo]:
    """Parse ``{module: source}`` and classify every top-level class."""
    return classify_trees({m: ast.parse(s, filename=m) for m, s in sources.items()})


def classify_paths(paths: list[str]) -> dict[str, ClassInfo]:
    """Read and classify every ``.py`` file under ``paths`` (domain packages)."""
    sources: dict[str, str] = {}
    for root in paths:
        if os.path.isfile(root):
            files = [root]
        else:
            files = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
                files.extend(os.path.join(dirpath, n) for n in filenames if n.endswith(".py"))
        for path in files:
            with open(path, encoding="utf-8") as fh:
                sources[path] = fh.read()
    return classify_sources(sources)
