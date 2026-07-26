"""Shared AST helpers used by both the classifier and the checks.

Kept in their own module so ``classify`` and ``checks`` can each depend on them
without depending on each other.
"""

import ast


def _name_of(node: ast.expr) -> str | None:
    """The bare name of a ``Name``/``Attribute`` decorator target."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_true(node: ast.expr) -> bool:
    """A truthy constant — matching dataclass runtime semantics, where
    ``frozen=1`` freezes exactly like ``frozen=True``. A non-constant
    expression stays False (conservative)."""
    return isinstance(node, ast.Constant) and bool(node.value)


def _dataclass_frozen(decorators: list[ast.expr]) -> tuple[bool, bool, ast.expr | None]:
    """(is_dataclass, is_frozen, decorator_node) for a class's decorator list.

    The decorator node is where TB001 points and where a ``# tessercheck:ignore`` is
    expected — it's the ``@dataclass`` line the user would change to add
    ``frozen=True``, not the ``class`` line the ClassDef reports.
    """
    for dec in decorators:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if _name_of(target) != "dataclass":
            continue
        frozen = False
        if isinstance(dec, ast.Call):
            for kw in dec.keywords:
                if kw.arg == "frozen" and _is_true(kw.value):
                    frozen = True
        return True, frozen, dec
    return False, False, None


def _dataclass_init_false(decorators: list[ast.expr]) -> bool:
    """True when the ``@dataclass`` decorator declares a falsy ``init`` — the
    explicit signal that the class hand-writes its own construction path (the
    spec-taking ``__init__`` of a compound value object / entity). Falsy by
    constant value (``init=False`` / ``init=0``), mirroring what the dataclass
    machinery does at runtime."""
    for dec in decorators:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if _name_of(target) != "dataclass":
            continue
        if isinstance(dec, ast.Call):
            for kw in dec.keywords:
                if (
                    kw.arg == "init"
                    and isinstance(kw.value, ast.Constant)
                    and not kw.value.value
                ):
                    return True
        return False
    return False


# Guarding every parse of a string annotation's CONTENT. That text is the one
# thing a checker parses that the outer file never had to, so it is the one
# place a legal file can defeat the parser: a long flat expression exhausts
# CPython's parser recursion, and RecursionError is not a SyntaxError — catching
# only that once aborted an entire run on a file that parsed fine. Failing
# closed (crediting no name) is the safe direction everywhere this is used.
_FORWARD_REF_PARSE_FAILURES = (SyntaxError, ValueError, RecursionError, MemoryError)

_MAX_ANNOTATION_DEPTH = 8


def _parse_forward_ref(text: str) -> ast.expr | None:
    try:
        return ast.parse(text, mode="eval").body
    except _FORWARD_REF_PARSE_FAILURES:
        return None


def _annotation_base(ann: ast.expr, depth: int = 0) -> str | None:
    """Base name of an annotation: ``list[X]``/``List[X]``/``list`` -> ``list``.

    A string annotation is a forward reference — ``"list[X]"`` has the same base
    as ``list[X]``. A quoted annotation is the ordinary way to name a type
    before it exists, not an escape hatch from any check keyed on this base."""
    if depth > _MAX_ANNOTATION_DEPTH:
        return None
    if isinstance(ann, ast.Name):
        return ann.id
    if isinstance(ann, ast.Subscript):
        return _annotation_base(ann.value, depth + 1)
    if isinstance(ann, ast.Attribute):
        return ann.attr
    if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
        parsed = _parse_forward_ref(ann.value)
        return None if parsed is None else _annotation_base(parsed, depth + 1)
    return None


# Subscript bases whose contents are NOT the annotated value. An annotation of
# ``type[LinkSpec]`` names the CLASS, and ``Callable[[], LinkSpec]`` a factory —
# neither IS a LinkSpec, so a caller asking "what does this annotation return"
# must not be credited with the names inside them.
_NOT_THE_VALUE: frozenset[str] = frozenset({"type", "Type", "Callable"})


def _annotation_names(ann: ast.expr | None, *, returned_only: bool = False) -> frozenset[str]:
    """Every type name in an annotation, string forward references resolved.

    ``"Slug"``, ``Slug | None`` and ``Optional["Slug"]`` all yield ``Slug`` — a
    wrapper is not an escape hatch, and a quoted annotation is the ordinary way
    to name your own class before it exists. This is the ONE walk shared by the
    classifier and every annotation-reading check; it diverged into three copies
    once, and only the newest had the forward-reference fix, so every
    classifier-keyed check kept the false positive the newest had already
    repaired.

    ``returned_only=True`` skips the contents of ``type[X]`` / ``Callable[..., X]``
    — for a caller asking what a function RETURNS (TB017's own-type door, TB032's
    spec-building helper), where X is mentioned without being produced. The
    default keeps them: a ban keyed on "any name anywhere" (the accessor-primitive
    net, the classifier's field census) must stay wide.
    """
    if ann is None:
        return frozenset()
    names: set[str] = set()

    def visit(node: ast.expr, depth: int = 0) -> None:
        if depth > _MAX_ANNOTATION_DEPTH:
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parsed = _parse_forward_ref(node.value)
            if parsed is not None:
                visit(parsed, depth + 1)
            return
        if isinstance(node, ast.Subscript):
            if returned_only and _annotation_base(node.value) in _NOT_THE_VALUE:
                return
            visit(node.value, depth + 1)
            visit(node.slice, depth + 1)
            return
        if isinstance(node, ast.Name):
            names.add(node.id)
            return
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                visit(child, depth + 1)

    visit(ann)
    return frozenset(names)


def _is_str_call(node: ast.expr) -> bool:
    """``str(x)`` or ``x.__str__()`` — a stringification, not a value."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "str" and len(node.args) == 1:
        return True
    if isinstance(func, ast.Attribute) and func.attr == "__str__":
        return True
    return False
