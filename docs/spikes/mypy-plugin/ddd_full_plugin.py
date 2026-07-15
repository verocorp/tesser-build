"""Full 4-check port of ddd-vet-py's checks.py as ONE mypy plugin.

DDD001 frozen-dataclass       -> get_class_decorator_hook_2("dataclasses.dataclass")
DDD002 hashable-fields        -> same hook, walks resolved field types post-default-callback
DDD003 no-setattr-bypass      -> get_method_hook("builtins.object.__setattr__")
DDD004 no-string-equality     -> get_method_hook("builtins.str.__eq__")

Faithfulness note: DDD001/002/003 in the AST tool are exempt in test files
(is_test_path); DDD004 fires everywhere. This plugin does not replicate the
test-path exemption (mypy plugin hooks don't see the file's test-ness for
free without checking ctx.api.path) -- omitted for the difficulty spike,
noted as a gap.
"""
from __future__ import annotations

from mypy.plugin import Plugin, ClassDefContext, MethodContext
from mypy.plugins.dataclasses import dataclass_class_maker_callback
from mypy.types import Instance, UnionType, NoneType, ProperType, get_proper_type
from mypy.nodes import (
    AssignmentStmt,
    CallExpr,
    NameExpr,
    MemberExpr,
    ComparisonExpr,
    Var,
)

_MUTABLE_COLLECTION_FULLNAMES = {"builtins.list", "builtins.dict", "builtins.set"}

# Bonus (not one of DDD001-004): a field whose RESOLVED type is a raw
# primitive -- ported verbatim from the prior single-check spike
# (mypy-spike/ddd_mypy_plugin.py PRIMITIVE_FULLNAMES), reused here to build
# the type-aware adversarial cases for the coordinator's matrix (alias /
# cross-module import / NewType). Not a registered ddd-vet-py code.
_PRIMITIVE_FULLNAMES = {
    "builtins.str",
    "builtins.int",
    "builtins.float",
    "builtins.bool",
    "builtins.bytes",
    "decimal.Decimal",
}


def _unwrap_optional(typ: ProperType) -> ProperType:
    if isinstance(typ, UnionType):
        non_none = [t for t in typ.items if not isinstance(get_proper_type(t), NoneType)]
        if len(non_none) == 1:
            return get_proper_type(non_none[0])
    return typ


# ---------------------------------------------------------------------------
# DDD001 + DDD002 : class-decorator hook
# ---------------------------------------------------------------------------


def dataclass_hook(ctx: ClassDefContext) -> bool:
    # MUST call the default callback first or __init__ synthesis silently
    # breaks for every dataclass in the checked tree (chain-preemption trap,
    # proven in the prior spike: mypy/plugin.py L902-905 first-match-wins,
    # mypy/build.py L746 custom_plugins before default_plugin).
    ok = dataclass_class_maker_callback(ctx)

    info = ctx.cls.info
    frozen = bool(info.metadata.get("dataclass", {}).get("frozen", False))

    # DDD001 -------------------------------------------------------------
    if not frozen:
        ctx.api.fail(
            f'DDD001: dataclass "{info.name}" is not frozen; domain values must '
            "be @dataclass(frozen=True)",
            ctx.cls,
        )
        return ok  # unframed dataclasses skip DDD002 (mirrors AST: only frozen dcs checked)

    # DDD002 -------------------------------------------------------------
    for stmt in ctx.cls.defs.body:
        # direct class-body annotated assignments only (mirrors AST version's
        # `isinstance(stmt, ast.AnnAssign)` restriction) -- mypy represents
        # `field: T` / `field: T = default` as AssignmentStmt with .type set
        # (mypy/nodes.py AssignmentStmt, L1845-1875).
        if not isinstance(stmt, AssignmentStmt) or stmt.type is None:
            continue
        field_name = None
        if len(stmt.lvalues) == 1 and isinstance(stmt.lvalues[0], NameExpr):
            field_name = stmt.lvalues[0].name
        rtype = get_proper_type(stmt.type)
        rtype = _unwrap_optional(rtype)
        if isinstance(rtype, Instance):
            if rtype.type.fullname in _MUTABLE_COLLECTION_FULLNAMES:
                ctx.api.fail(
                    f'DDD002: frozen dataclass "{info.name}" field '
                    f'"{field_name}" is a mutable collection '
                    f"({rtype.type.fullname.split('.')[-1]}); __hash__ raises "
                    "at runtime -- use tuple/frozenset",
                    ctx.cls,
                )
                continue
            # Bonus attempt: a CUSTOM class field that is itself unhashable.
            # mypy does NOT statically synthesize `__hash__ = None` for a
            # class that defines __eq__ without __hash__ (that is a CPython
            # runtime rule, not something semanal.py models -- confirmed by
            # grepping mypy/semanal.py: no synthesis site exists). So we
            # replicate the CPython rule ourselves: own __eq__, no own
            # __hash__ (checking rtype.type.names, the class's OWN symbol
            # table, not the inherited MRO) => unhashable at runtime.
            own_names = rtype.type.names
            if "__eq__" in own_names and "__hash__" not in own_names:
                ctx.api.fail(
                    f'DDD002: frozen dataclass "{info.name}" field '
                    f'"{field_name}" has type "{rtype.type.fullname}" which '
                    "defines __eq__ without __hash__ -- unhashable at "
                    "runtime (CPython sets __hash__ = None)",
                    ctx.cls,
                )
                continue
            # Bonus (matrix cases I/K/L, not a DDD00x code): raw primitive
            # field, resolved through alias / cross-module import. A NewType
            # gets its OWN synthetic TypeInfo (fullname is the NewType's own
            # qualified name, not "builtins.int"), so it is correctly left
            # alone here -- matches the prior spike's proven behavior.
            if rtype.type.fullname in _PRIMITIVE_FULLNAMES:
                ctx.api.fail(
                    f'PRIMITIVE: frozen dataclass "{info.name}" field '
                    f'"{field_name}" has a raw primitive type '
                    f"({rtype.type.fullname}); use a value object instead",
                    ctx.cls,
                )
    return ok


# ---------------------------------------------------------------------------
# DDD003 : method hook on object.__setattr__
# ---------------------------------------------------------------------------


def setattr_hook(ctx: MethodContext):
    # ctx.api is the real TypeChecker (mypy/checkexpr.py L1286-1296 passes
    # api=self.chk). CheckerPluginInterface (mypy/plugin.py L224-252) does NOT
    # declare .scope -- this is undocumented duck-typed access to the
    # concrete TypeChecker's CheckerScope (mypy/checker.py L493, L581;
    # mypy/checker_shared.py L302-320 CheckerScope.current_function()).
    scope = getattr(ctx.api, "scope", None)
    in_post_init = False
    if scope is not None:
        fn = scope.current_function()
        in_post_init = fn is not None and getattr(fn, "name", None) == "__post_init__"
    if not in_post_init:
        ctx.api.fail(
            "DDD003: object.__setattr__ bypasses frozen immutability outside "
            "__post_init__; a value object never mutates after construction",
            ctx.context,
        )
    return ctx.default_return_type


# ---------------------------------------------------------------------------
# DDD004 : method hook on str.__eq__ (fires on every str == comparison)
# ---------------------------------------------------------------------------


def _is_str_call(node) -> bool:
    if not isinstance(node, CallExpr):
        return False
    callee = node.callee
    if isinstance(callee, NameExpr) and callee.fullname == "builtins.str" and len(node.args) == 1:
        return True
    if isinstance(callee, MemberExpr) and callee.name == "__str__":
        return True
    return False


def str_eq_hook(ctx: MethodContext):
    # ctx.context is the whole ComparisonExpr (mypy/checkexpr.py
    # visit_comparison_expr L3709-3826 passes context=e, the ComparisonExpr,
    # into check_op -> check_method_call -> MethodContext). It carries
    # .operands, so we can inspect BOTH sides syntactically -- something a
    # method hook triggered by only one operand's type would not otherwise
    # give us.
    cmp = ctx.context
    if isinstance(cmp, ComparisonExpr):
        for left, right, op in zip(cmp.operands, cmp.operands[1:], cmp.operators):
            if op == "==" and _is_str_call(left) and _is_str_call(right):
                ctx.api.fail(
                    "DDD004: equality by str() representation mis-equates "
                    "multi-representation value objects; compare by value",
                    cmp,
                )
    return ctx.default_return_type


class DDDFullPlugin(Plugin):
    def get_class_decorator_hook_2(self, fullname: str):
        if fullname == "dataclasses.dataclass":
            return dataclass_hook
        return None

    def get_method_hook(self, fullname: str):
        if fullname == "builtins.object.__setattr__":
            return setattr_hook
        if fullname == "builtins.str.__eq__":
            return str_eq_hook
        return None


def plugin(version: str):
    return DDDFullPlugin
