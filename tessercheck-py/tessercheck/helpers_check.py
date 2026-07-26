"""TB032 — the test-helper norm (``skills/tesser-build/testing.md``).

A helper in a test module builds a **spec or a DTO** and nothing else. It never
returns a constructed domain object (that is built at the call site, in the
test, where the reader can see it), and it never carries logic — an argument
that reaches a helper either replaces a default or does not belong there.

This is a **totality** check, which is what makes it different in kind from the
rest of the analyzer: it does not hunt for a known-bad shape, it requires every
module-level function in a test module to classify. What does not classify is
reported, and the report is a worklist rather than an accusation — the function
may be fine and merely undeclarable, in which case it says so with a marker.

Two categories are decided structurally, so conformant code needs no annotation:

* a function whose return annotation names a **spec** in the whole-tree
  classifier registry (the classifier calls an inert public-field frozen
  dataclass a ``SPEC``, which is the same shape a DTO has — so this arm covers
  both of the sanctioned kinds);
* a function decorated ``@pytest.fixture``.

Anything else declares itself with ``# tesser-category: <name>`` from the closed
set in :mod:`tessercheck.markers`, on the line above the definition or trailing
its ``def``.

Spec resolution reads the shared registry **and the file's own classes**. The
shared registry excludes test files on purpose — a test fake must not shadow a
domain type in a tree-wide registry — but that is a rule about *shadowing*, not
a reason to deny this check local knowledge. A helper that returns a spec is
conformant wherever that spec is declared, and a wire-shape DTO declared beside
the tests that exercise it is an ordinary thing to do. Without the local pass
every such helper would need a marker to say what the code already says.

What is left for the marker is what no annotation can settle: a return type that
names nothing classifiable (a ``dict`` payload, an ``Iterator``), or a shape
whose category a reader knows and the checker cannot infer.

**Scope: module-level functions only, and that is measured rather than assumed.**
Every non-test *method* on a class inside the two gated example trees is a
hand-written fake implementing a collaborator's interface — ``save``/``load`` on
a repository fake, ``check`` on a policy fake. That is the shape TB030
*requires*. Judging methods would flag some forty instances of the norm's own
mandated construct, so the check would be reporting the right answer as a
violation.

**Test detection is structural, and it WALKS.** A module is a test module when
it defines a ``test_*`` function *at any depth* — never by the ``is_test`` path
flag, which would make the fixtures unprovable. The depth matters: pytest's
class style puts every test on a ``Test*`` class, so a scan of ``tree.body``
alone sees no tests, exempts the whole file, and takes its module-level helpers
with it. That is not hypothetical — ``examples/python/tests/test_short_link.py``
is exactly this shape, and its ``_spec`` helper is precisely what TB032 exists
to judge.

**Known hole.** A module with no ``test_*`` function anywhere — a helper-only
module beside the tests, or a ``conftest.py`` — is never judged at all. Closing
it means deciding what makes a *non-test* module part of the test tree, which is
a scoping question this check does not answer. It is recorded here rather than
papered over.
"""

import ast
import io
import tokenize

from tessercheck.astutil import _annotation_base
from tessercheck.classify import ClassInfo, Stereotype, classify_trees
from tessercheck.finding import Finding
from tessercheck.markers import (
    CATEGORY_PREFIX,
    category_list,
    declared_category,
    is_known_category,
)

_SUPPRESS_MARKER = "# tessercheck:ignore"

_UNCATEGORIZED_MSG = (
    "test-module function {name!r} does not classify as a test helper — a "
    "helper builds a spec or a DTO (never a constructed domain object, which "
    "belongs at the call site in the test) and a fixture is decorated "
    "@pytest.fixture. If it is one of those but the checker cannot see it, "
    "declare it with '# {prefix} <{categories}>'; if it is neither, it is "
    "logic wearing a helper's clothes and belongs outside the test tree "
    "(skills/tesser-build/testing.md)"
)

_UNKNOWN_CATEGORY_MSG = (
    "unknown test-helper category {name!r} — the set is closed "
    "({categories}). A category is added when a shape earns one from "
    "evidence, never to silence a flag (skills/tesser-build/testing.md)"
)


def _is_test_function(node: ast.AST) -> bool:
    return (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _defines_a_test(tree: ast.Module) -> bool:
    return any(_is_test_function(node) for node in ast.walk(tree))


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
    return False


# Subscript bases whose contents are NOT the returned value. A helper returning
# ``type[LinkSpec]`` returns the CLASS, and one returning ``Callable[[], LinkSpec]``
# returns a factory — neither is a built spec, so crediting the name inside them
# would bless a function that does something else entirely.
_NOT_THE_VALUE: frozenset[str] = frozenset({"type", "Type", "Callable"})


def _annotation_names(ann: ast.expr) -> frozenset[str]:
    """Every type name the annotation actually RETURNS.

    Two things this has to get right, both found by adversarial review:

    * A **string annotation** is a forward reference — ``-> "LinkSpec"`` and
      ``-> list["LinkSpec"]`` carry no ``ast.Name`` at all, so a plain walk saw
      nothing and reported a conformant helper. Idiomatic Python, and this
      analyzer runs in other people's CI, so the false positive is the expensive
      kind. Parse the string and recurse.
    * ``type[X]`` / ``Callable[..., X]`` mention X without returning one.
    """
    names: set[str] = set()

    def visit(node: ast.expr, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                parsed = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return
            visit(parsed, depth + 1)
            return
        if isinstance(node, ast.Subscript):
            if _annotation_base(node.value) in _NOT_THE_VALUE:
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


def _returns_a_spec(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    registry: dict[str, ClassInfo],
    local: dict[str, ClassInfo],
) -> bool:
    if node.returns is None:
        return False
    return any(
        (info := registry.get(name) or local.get(name)) is not None
        and info.stereotype is Stereotype.SPEC
        for name in _annotation_names(node.returns)
    )


def _comment_lines(source: str) -> dict[int, str]:
    try:
        return {
            token.start[0]: token.string
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type == tokenize.COMMENT
        }
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fail closed: with no comments read, no marker is honored and every
        # undeclarable function reports. A marker that silently stops working is
        # the failure worth avoiding here.
        return {}


def _anchor_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    lines = [node.lineno]
    lines.extend(int(getattr(d, "lineno", node.lineno)) for d in node.decorator_list)
    return min(lines)


def _declared_on(
    node: ast.FunctionDef | ast.AsyncFunctionDef, comments: dict[int, str]
) -> str | None:
    """The category declared for ``node``: the contiguous comment block directly
    above its first line, or a marker trailing that line.

    Contiguous with no blank line between, deliberately. A marker separated from
    its definition attaches to nothing in particular, and walking up through
    blank lines would let it reach the previous function's trailing comment
    instead.
    """
    anchor = _anchor_line(node)
    if (trailing := comments.get(anchor)) is not None:
        if (name := declared_category(trailing)) is not None:
            return name
    line = anchor - 1
    while (comment := comments.get(line)) is not None:
        if (name := declared_category(comment)) is not None:
            return name
        line -= 1
    return None


def check_helpers(
    path: str,
    source: str,
    tree: ast.Module,
    registry: dict[str, ClassInfo],
) -> list[Finding]:
    """Every TB032 finding for one file. Silent unless the module defines a
    ``test_*`` function somewhere in it."""
    if not _defines_a_test(tree):
        return []

    comments = _comment_lines(source)
    suppressed = {
        line for line, text in comments.items() if _SUPPRESS_MARKER in text
    }
    local = classify_trees({path: tree})

    findings: list[Finding] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _is_test_function(node):
            continue
        anchor = _anchor_line(node)
        if anchor in suppressed or node.lineno in suppressed:
            continue

        declared = _declared_on(node, comments)
        if declared is not None:
            if not is_known_category(declared):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        node.col_offset + 1,
                        "TB032",
                        _UNKNOWN_CATEGORY_MSG.format(
                            name=declared, categories=category_list()
                        ),
                    )
                )
            continue

        if _is_fixture(node) or _returns_a_spec(node, registry, local):
            continue

        findings.append(
            Finding(
                path,
                node.lineno,
                node.col_offset + 1,
                "TB032",
                _UNCATEGORIZED_MSG.format(
                    name=node.name,
                    prefix=CATEGORY_PREFIX,
                    categories=category_list(),
                ),
            )
        )
    return findings
