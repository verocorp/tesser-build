"""The per-file AST checks. One ``ast.NodeVisitor`` produces every
:class:`Finding` for TB001-004.

Most are deliberately *syntactic* — they read the shape of the code:

* **TB001** (frozen) is the gateway: a non-frozen dataclass classifies as
  ``OTHER``, so it *cannot* be keyed on the value-object stereotype (the
  classifier uses frozen-ness to recognise a VO). It stays a shape check.
* **TB003** (setattr-bypass) and **TB004** (str-equality) are shape/expression
  checks with no stereotype dependency.
* **TB002** (hash-hazard) is the exception — it is **classification-aware**: the
  "back a collection with a tuple" rule is a *value-object* rule, so it fires
  only on a class classified ``VALUE_OBJECT``. A frozen dataclass that is really
  a spec / persistence row (public primitive fields, no validation) is a ``SPEC``
  and is exempt — that is what stops a repo row's ``dict`` field tripping TB002.
"""

import ast

from tessercheck.astutil import _annotation_base, _dataclass_frozen, _is_str_call
from tessercheck.classify import ClassInfo, Stereotype, classify_trees
from tessercheck.comments_check import check_comments
from tessercheck.finding import Finding
from tessercheck.typed_checks import check_typed

# Annotation base names that make a frozen dataclass unhashable at runtime
# (``__hash__`` raises when the instance is used as a set element / dict key).
# ``tuple`` and ``frozenset`` are hashable and therefore allowed — which is why
# the collection value object in the examples backs itself with a sorted tuple.
_MUTABLE_COLLECTIONS: frozenset[str] = frozenset(
    {
        "list",
        "dict",
        "set",
        "List",
        "Dict",
        "Set",
        "DefaultDict",
        "defaultdict",
        "OrderedDict",
        "Counter",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
    }
)

_SUPPRESS_MARKER = "# tessercheck:ignore"


class _Checker(ast.NodeVisitor):
    def __init__(
        self,
        path: str,
        source: str,
        is_test: bool,
        registry: dict[str, ClassInfo],
    ) -> None:
        self._path = path
        self._lines = source.splitlines()
        self._is_test = is_test
        self._registry = registry
        self._func_stack: list[str] = []
        self.findings: list[Finding] = []

    def _is_value_object(self, name: str) -> bool:
        info = self._registry.get(name)
        return info is not None and info.stereotype is Stereotype.VALUE_OBJECT

    # -- emit ---------------------------------------------------------------

    def _suppressed(self, line: int) -> bool:
        if 1 <= line <= len(self._lines):
            return _SUPPRESS_MARKER in self._lines[line - 1]
        return False

    def _emit(self, node: ast.AST, code: str, message: str) -> None:
        line = int(getattr(node, "lineno", 0))
        col = int(getattr(node, "col_offset", 0)) + 1
        if self._suppressed(line):
            return
        self.findings.append(Finding(self._path, line, col, code, message))

    # -- visitors -----------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        is_dc, frozen, dec = _dataclass_frozen(node.decorator_list)
        if is_dc and not frozen and not self._is_test and dec is not None:
            # TB001 — a mutable dataclass modeling a domain value.
            self._emit(
                dec,
                "TB001",
                f"dataclass {node.name!r} is not frozen; domain values must be "
                "@dataclass(frozen=True) (immutability + value equality)",
            )
        if is_dc and frozen and not self._is_test:
            self._check_hashable_fields(node)
        self.generic_visit(node)

    def _check_hashable_fields(self, node: ast.ClassDef) -> None:
        # TB002 — a value-object rule: back a collection with a tuple/frozenset.
        # A frozen dataclass that is a spec / persistence row (a SPEC) is exempt;
        # only a class classified VALUE_OBJECT is checked.
        if not self._is_value_object(node.name):
            return
        # Only direct class-body fields (AnnAssign), never locals or instance
        # attributes inside methods.
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            base = _annotation_base(stmt.annotation)
            if base in _MUTABLE_COLLECTIONS:
                target = stmt.target
                field = target.id if isinstance(target, ast.Name) else "<field>"
                self._emit(
                    stmt,
                    "TB002",
                    f"frozen dataclass {node.name!r} field {field!r} is a mutable "
                    f"collection ({base}); its __hash__ raises at runtime — use a "
                    "tuple/frozenset (sort/canonicalize in __post_init__)",
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._func_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._func_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._func_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        # TB003 — object.__setattr__/__delattr__ bypassing frozen immutability,
        # allowed only inside __post_init__ (construction-time canonicalization).
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"__setattr__", "__delattr__"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "object"
            and not self._is_test
            and "__post_init__" not in self._func_stack
        ):
            self._emit(
                node,
                "TB003",
                f"object.{func.attr} bypasses frozen immutability outside "
                "__post_init__; a value object never mutates after construction",
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # TB004 — equality by string representation. Fire only when the
        # comparison is == and BOTH sides are str()/__str__() calls, so a lone
        # display call or a literal compare (x.__str__() == "USD 100") is safe.
        if (
            len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and _is_str_call(node.left)
            and _is_str_call(node.comparators[0])
        ):
            self._emit(
                node,
                "TB004",
                "equality by str() representation mis-equates multi-representation "
                "value objects; compare by value (== / a hand-written __eq__)",
            )
        self.generic_visit(node)


def check_tree(
    path: str,
    source: str,
    tree: ast.Module,
    is_test: bool,
    registry: dict[str, ClassInfo],
) -> list[Finding]:
    """Every finding for one already-parsed file, against a shared registry.

    The syntactic checks (TB001-004) read only this file's shape. The
    classification-aware checks (TB010+) key on ``registry`` — which
    ``run_paths`` builds across the *whole tree*, so cross-file embedding
    (``embeds_entity``, ``is_member``) resolves. Test files are exempt from the
    typed checks (they legitimately construct and exercise domain objects).
    """
    checker = _Checker(path, source, is_test, registry)
    checker.visit(tree)
    findings = list(checker.findings)
    if not is_test:
        findings.extend(check_typed(registry, path, tree, source))
    # TB020 has no test exemption — the comments norm covers the whole tree.
    findings.extend(check_comments(path, source, tree))
    return sorted(findings, key=lambda f: (f.line, f.col, f.code))


def check_source(
    path: str,
    source: str,
    is_test: bool,
    registry: dict[str, ClassInfo] | None = None,
) -> list[Finding]:
    """Parse ``source`` and return every finding, sorted by location.

    Single-file entry point (CLI on one file, unit tests). When ``registry`` is
    omitted, the file is classified *in isolation* — correct for axis-1
    stereotypes (identity signals are local) but blind to cross-file embedding;
    ``run_paths`` passes a whole-tree registry so embedding resolves.
    """
    tree = ast.parse(source, filename=path)
    if registry is None:
        registry = classify_trees({path: tree})
    return check_tree(path, source, tree, is_test, registry)
