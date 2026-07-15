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

from ddd_vet.astutil import _annotation_base, _dataclass_frozen

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
    an entity in the state of owning + guarding a collection), so the aggregate
    role is a structural attribute (:attr:`ClassInfo.owns_collection`), not a
    separate stereotype.
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
    owns_collection: bool
    is_member: bool
    # local signals (pass 1) — retained so checks needn't re-derive them
    frozen_dataclass: bool
    has_post_init: bool
    has_underscore_field: bool
    has_eq_none: bool
    has_eq_method: bool
    field_type_names: frozenset[str]
    collection_element_names: frozenset[str]


def _all_names(node: ast.expr) -> frozenset[str]:
    """Every ``Name``/``Attribute`` identifier anywhere in an annotation."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return frozenset(names)


def _collection_element_names(ann: ast.expr) -> frozenset[str]:
    """Element type names of a collection annotation (``list[ShortLink]`` ->
    ``{ShortLink}``); empty for a non-collection annotation."""
    if isinstance(ann, ast.Subscript) and _annotation_base(ann.value) in _COLLECTION_BASES:
        return _all_names(ann.slice)
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
    has_method: bool
    has_post_init: bool
    has_underscore_field: bool
    has_eq_none: bool
    has_eq_method: bool
    field_type_names: frozenset[str]
    collection_element_names: frozenset[str]


def _scan_class(node: ast.ClassDef, module: str) -> _Scan:
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
                # A plain-class entity/aggregate declares its composition through
                # __init__ parameter annotations, not class-level fields.
                params = [*stmt.args.posonlyargs, *stmt.args.args, *stmt.args.kwonlyargs]
                for arg in params:
                    if arg.arg == "self" or arg.annotation is None:
                        continue
                    field_types |= _all_names(arg.annotation)
                    collection_elems |= _collection_element_names(arg.annotation)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fname = stmt.target.id
            if fname.startswith("_"):
                has_underscore_field = True
            field_types |= _all_names(stmt.annotation)
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
        has_method=bool(methods),
        has_post_init="__post_init__" in methods,
        has_underscore_field=has_underscore_field,
        has_eq_none=has_eq_none,
        has_eq_method="__eq__" in methods,
        field_type_names=frozenset(field_types),
        collection_element_names=frozenset(collection_elems),
    )


def _local_stereotype(scan: _Scan) -> Stereotype:
    """Axis 1 — kind of identity, from local signals only."""
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
        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef):
                scan = _scan_class(stmt, module)
                scans[scan.name] = scan
                stereos[scan.name] = _local_stereotype(scan)

    domain = {n for n, s in stereos.items() if s in (Stereotype.VALUE_OBJECT, Stereotype.IDENTITY_OBJECT)}

    registry: dict[str, ClassInfo] = {}
    for name, scan in scans.items():
        stereo = stereos[name]
        owns = bool(scan.collection_element_names & domain)
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
            owns_collection=owns,
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
