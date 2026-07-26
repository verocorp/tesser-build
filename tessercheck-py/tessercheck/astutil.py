"""Shared AST helpers used by both the classifier and the checks.

Kept in their own module so ``classify`` and ``checks`` can each depend on them
without depending on each other.
"""

import ast
from collections.abc import Iterator


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

# Bounds RE-ENTRY through parsed string annotations only — a string whose
# content is itself a quoted string, eight quotes deep, is nobody's type.
# Plain AST descent is NOT depth-capped: a ban keyed on "any name anywhere"
# must stay wide, and capping ordinary generic nesting silently turned
# ``dict[str, dict[str, ...]]`` five levels deep into an escape hatch from
# TB010 (adversarial review of the first cut of this module).
_MAX_FORWARD_REF_DEPTH = 8


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
    if depth > _MAX_FORWARD_REF_DEPTH:
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


def _annotation_refs(
    ann: ast.expr | None, *, returned_only: bool = False
) -> Iterator[tuple[str | None, ast.expr]]:
    """Yield ``(name, position_carrier)`` for every type name an annotation
    names, string forward references resolved. A ``None`` name marks a string
    the walk treated as a forward reference and could not parse — the signal
    that the annotation cannot be taken at its word. Keeping that signal inside
    the one traversal is deliberate: an earlier cut computed it with a second
    independent ``ast.walk``, which disagreed with this walk on both nested
    quotes (garbage one quote deep went unseen) and Literal/Annotated strings
    (values were parsed as types here and skipped there).

    The carrier is the node a report should point at: the ``Name``/``Attribute``
    itself, or — for a name found inside a string annotation — the outermost
    string ``Constant``, since the string's content has no position of its own
    in the outer file.

    Two string contexts are NOT forward references and are skipped (adversarial
    review caught both firing on conformant code): the values of a
    ``Literal[...]`` — ``Literal["Warehouse"]`` is a discriminator holding a
    string, not the type it happens to spell — and the metadata arguments of
    ``Annotated[X, ...]``, where only ``X`` is the type. The skip is keyed on
    the spelled base name, so an import alias (``Literal as L``) defeats it —
    the alias-disguise class this analyzer scopes out everywhere.

    Iterative on an explicit stack: the deleted copies used ``ast.walk``, which
    no annotation could blow the interpreter stack on, and this walk must not
    be weaker.
    """
    if ann is None:
        return
    stack: list[tuple[ast.expr, int, ast.expr | None]] = [(ann, 0, None)]
    while stack:
        node, string_depth, carrier = stack.pop()
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if string_depth >= _MAX_FORWARD_REF_DEPTH:
                continue
            parsed = _parse_forward_ref(node.value)
            if parsed is not None:
                stack.append((parsed, string_depth + 1, carrier or node))
            else:
                yield None, (carrier if carrier is not None else node)
            continue
        if isinstance(node, ast.Subscript):
            base = _annotation_base(node.value)
            if returned_only and base in _NOT_THE_VALUE:
                continue
            if base == "Literal":
                stack.append((node.value, string_depth, carrier))
                continue
            if base == "Annotated":
                stack.append((node.value, string_depth, carrier))
                if isinstance(node.slice, ast.Tuple) and node.slice.elts:
                    stack.append((node.slice.elts[0], string_depth, carrier))
                else:
                    stack.append((node.slice, string_depth, carrier))
                continue
            stack.append((node.value, string_depth, carrier))
            stack.append((node.slice, string_depth, carrier))
            continue
        if isinstance(node, ast.Name):
            yield node.id, (carrier if carrier is not None else node)
            continue
        if isinstance(node, ast.Attribute):
            yield node.attr, (carrier if carrier is not None else node)
            continue
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                stack.append((child, string_depth, carrier))


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
    return frozenset(
        name
        for name, _ in _annotation_refs(ann, returned_only=returned_only)
        if name is not None
    )


def _has_unparseable_forward_ref(ann: ast.expr | None, *, returned_only: bool = False) -> bool:
    """True when any string the walk treats as a forward reference fails to
    parse — the signal that the annotation as a whole cannot be taken at its
    word, so a caller should fall back to inspecting the body. ``not
    _annotation_names(...)`` alone is not that signal: ``tuple["int", "not (("]``
    credits ``tuple`` and ``int`` while silently dropping the garbage part.
    Same traversal as the names — pass the same ``returned_only`` the name set
    was computed with — so nested quotes are seen through, a Literal value /
    Annotated metadata string is never mistaken for garbage, and garbage inside
    an excluded ``type[...]``/``Callable[...]`` slot cannot discredit an
    annotation whose returned value reads cleanly."""
    return any(
        name is None for name, _ in _annotation_refs(ann, returned_only=returned_only)
    )


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
