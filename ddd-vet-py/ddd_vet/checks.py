"""The AST checks. One ``ast.NodeVisitor`` produces every :class:`Finding`.

Each check is faithful to a rule in ``skills/ddd/python.md`` and is deliberately
*syntactic* — it reads the shape of the code, never resolved types. The checks
operate on dataclasses generically (VO / spec / DTO alike), because the rules
hold for all of them and that sidesteps the one genuinely hard call (VO vs
entity vs aggregate), which v1 does not need.
"""

import ast

from ddd_vet.astutil import _annotation_base, _dataclass_frozen, _is_str_call
from ddd_vet.classify import classify_trees
from ddd_vet.finding import Finding
from ddd_vet.typed_checks import check_typed

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

_SUPPRESS_MARKER = "# ddd:ignore"


class _Checker(ast.NodeVisitor):
    def __init__(self, path: str, source: str, is_test: bool) -> None:
        self._path = path
        self._lines = source.splitlines()
        self._is_test = is_test
        self._func_stack: list[str] = []
        self.findings: list[Finding] = []

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
            # DDD001 — a mutable dataclass modeling a domain value.
            self._emit(
                dec,
                "DDD001",
                f"dataclass {node.name!r} is not frozen; domain values must be "
                "@dataclass(frozen=True) (immutability + value equality)",
            )
        if is_dc and frozen and not self._is_test:
            self._check_hashable_fields(node)
        self.generic_visit(node)

    def _check_hashable_fields(self, node: ast.ClassDef) -> None:
        # DDD002 — only direct class-body fields (AnnAssign), never locals or
        # instance attributes inside methods.
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            base = _annotation_base(stmt.annotation)
            if base in _MUTABLE_COLLECTIONS:
                target = stmt.target
                field = target.id if isinstance(target, ast.Name) else "<field>"
                self._emit(
                    stmt,
                    "DDD002",
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
        # DDD003 — object.__setattr__/__delattr__ bypassing frozen immutability,
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
                "DDD003",
                f"object.{func.attr} bypasses frozen immutability outside "
                "__post_init__; a value object never mutates after construction",
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # DDD004 — equality by string representation. Fire only when the
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
                "DDD004",
                "equality by str() representation mis-equates multi-representation "
                "value objects; compare by value (== / a hand-written __eq__)",
            )
        self.generic_visit(node)


def check_source(path: str, source: str, is_test: bool) -> list[Finding]:
    """Parse ``source`` and return every finding, sorted by location.

    Runs the syntactic per-file checks (DDD001-004) and the classification-aware
    checks (DDD010+). The latter classify this single source into the stereotype
    registry — enough for per-class rules like VO exposure; whole-tree runs
    (``run_paths``) resolve cross-file embedding for the same registry.
    """
    tree = ast.parse(source, filename=path)
    checker = _Checker(path, source, is_test)
    checker.visit(tree)
    findings = list(checker.findings)
    if not is_test:
        registry = classify_trees({path: tree})
        findings.extend(check_typed(registry, path, tree, source))
    return sorted(findings, key=lambda f: (f.line, f.col, f.code))
