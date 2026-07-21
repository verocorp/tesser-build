"""The per-file AST checks. One ``ast.NodeVisitor`` produces every
:class:`Finding` for TB001-004.

Most are deliberately *syntactic* — they read the shape of the code:

* **TB001** (frozen) is the gateway: a non-frozen dataclass classifies as
  ``OTHER``, so it *cannot* be keyed on the value-object stereotype (the
  classifier uses frozen-ness to recognise a VO). It stays a shape check, and
  its scope is deliberately **total** — every dataclass in non-test code,
  specs and adapter DTOs included, must be frozen. Frozen costs a DTO
  nothing, and any stereotype/layer gate would open the exact hole the check
  exists to close: a would-be domain value hiding from classification by not
  being frozen. The escape for a genuinely mutable boundary shape is an
  inline ``# tessercheck:ignore``, a visible declared fact.
* **TB003** (setattr-bypass) and **TB004** (str-equality) are shape/expression
  checks with no stereotype dependency. TB003 allows the two construction
  sites and nothing else: ``__post_init__`` (canonicalization), and the
  spec-taking ``__init__`` of a ``@dataclass(frozen=True, init=False)`` class
  assigning its own declared fields — the shape TB013 prescribes, which has
  no other way to assign fields.
* **TB002** (hash-hazard) is the exception — it is **classification-aware**: the
  "back a collection with a tuple" rule is a *value-object* rule, so it fires
  only on a class classified ``VALUE_OBJECT``. A frozen dataclass that is really
  a spec / persistence row (public primitive fields, no validation) is a ``SPEC``
  and is exempt — that is what stops a repo row's ``dict`` field tripping TB002.
"""

import ast

from tessercheck.astutil import (
    _annotation_base,
    _dataclass_frozen,
    _dataclass_init_false,
    _is_str_call,
)
from tessercheck.classify import ClassInfo, Stereotype, classify_trees
from tessercheck.comments_check import check_comments
from tessercheck.finding import Finding
from tessercheck.test_double_check import check_test_doubles
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
        # (declares frozen=True AND init=False, declared field names, function
        # depth at class entry) per enclosing class — what the TB003
        # spec-__init__ exemption keys on. The depth pins the exemption to a
        # DIRECT class-body __init__: a nested def named __init__ sits deeper
        # than depth+1 and never inherits it.
        self._class_stack: list[tuple[bool, frozenset[str], int]] = []
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
            # TB001 — deliberately total: every dataclass, not just domain
            # values. Frozen costs a spec/DTO nothing, and a stereotype gate
            # would let a would-be domain value hide from classification by
            # staying non-frozen (the classifier keys VOs on frozen-ness).
            self._emit(
                dec,
                "TB001",
                f"dataclass {node.name!r} is not frozen; every dataclass is "
                "@dataclass(frozen=True) here — a domain value for "
                "immutability + value equality, a spec/DTO because frozen "
                "costs it nothing and a non-frozen dataclass is invisible to "
                "the VO classifier (annotate '# tessercheck:ignore' for a "
                "boundary shape that genuinely must mutate)",
            )
        if is_dc and frozen and not self._is_test:
            self._check_hashable_fields(node)
        # ClassVar/InitVar annotations are not instance fields to the dataclass
        # machinery, so they are not sanctioned setattr targets either.
        fields = frozenset(
            stmt.target.id
            for stmt in node.body
            if isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and _annotation_base(stmt.annotation) not in {"ClassVar", "InitVar"}
        )
        spec_init_shape = (
            is_dc and frozen and _dataclass_init_false(node.decorator_list)
        )
        self._class_stack.append((spec_init_shape, fields, len(self._func_stack)))
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()

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

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # A lambda is its own function frame: a setattr inside a lambda defined
        # in __init__ runs POST-construction (whenever the lambda is called),
        # so it must never inherit the spec-__init__ exemption.
        self._func_stack.append("<lambda>")
        try:
            self.generic_visit(node)
        finally:
            self._func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        # TB003 — object.__setattr__/__delattr__ bypassing frozen immutability.
        # Two construction sites are sanctioned: __post_init__ (canonicalization)
        # and the spec-taking __init__ of a frozen init=False dataclass assigning
        # its own declared fields — that shape has no other way in. Everything
        # else (any ordinary method, __delattr__ anywhere, a non-field name) is
        # post-construction mutation and stays flagged.
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"__setattr__", "__delattr__"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "object"
            and not self._is_test
            and "__post_init__" not in self._func_stack
            and not self._is_spec_init_assignment(node, func.attr)
        ):
            self._emit(
                node,
                "TB003",
                f"object.{func.attr} bypasses frozen immutability outside "
                "__post_init__ or the spec-taking __init__ of a "
                "@dataclass(frozen=True, init=False); a value object never "
                "mutates after construction",
            )
        self.generic_visit(node)

    def _is_spec_init_assignment(self, node: ast.Call, attr: str) -> bool:
        """The sanctioned construction write: ``object.__setattr__(self, "x", ...)``
        directly inside the class-body ``__init__`` of a
        ``@dataclass(frozen=True, init=False)`` class, where ``"x"`` is one of
        that class's declared instance fields. "Directly" is enforced by frame
        depth: the ``__init__`` must be the single function frame above the
        class entry — a nested def or lambda never inherits the exemption."""
        if attr != "__setattr__":
            return False
        if not (self._func_stack and self._func_stack[-1] == "__init__"):
            return False
        if not self._class_stack:
            return False
        spec_init_shape, fields, depth = self._class_stack[-1]
        if not spec_init_shape or len(self._func_stack) != depth + 1:
            return False
        if len(node.args) < 2:
            return False
        target, name = node.args[0], node.args[1]
        return (
            isinstance(target, ast.Name)
            and target.id == "self"
            and isinstance(name, ast.Constant)
            and isinstance(name.value, str)
            and name.value in fields
        )

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
    # TB030 is global too — the fakes-only norm bans mock libraries in domain
    # code and test code alike, and global scope keeps the bad.py fixture
    # provable with is_test=False.
    findings.extend(check_test_doubles(path, source, tree))
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
