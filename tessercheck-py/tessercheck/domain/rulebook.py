from __future__ import annotations

import ast
import re
from typing import Final

import tesser.domain as ts

import tessercheck.domain.checks as checks

HOLE_NAMES: Final[dict[str, str]] = {
    "where": "⟨module.Class.method⟩",
    "module.name()": "⟨module⟩",
    "cls.name": "⟨class⟩",
    "callee.attr": "⟨method⟩",
    "callee.id": "⟨function⟩",
    "len(params)": "⟨count⟩",
    "len(ports)": "⟨count⟩",
    "arg.arg": "⟨name⟩",
    "stmt.name": "⟨name⟩",
    "inner.name": "⟨class⟩",
    "type(node).__name__": "⟨node⟩",
    "span": "⟨count⟩",
    "target": "⟨import⟩",
    "package": "⟨package⟩",
    "self._export": "⟨export⟩",
    "declared": "⟨import⟩",
    "tier": "⟨tier⟩",
    "own_roles": "⟨roles⟩",
    "foreign_roles": "⟨roles⟩",
    "KIND_NAME[block]": "⟨kind⟩",
    "KIND_ROLE[block]": "⟨role⟩",
    "KIND_HOME[block]": "⟨role⟩",
    "enum_base": "⟨enum⟩",
    "KIND_NAME[touched]": "⟨kind⟩",
    "name": "⟨module⟩",
    "others": "⟨paths⟩",
    "error.msg": "⟨error⟩",
    "kind": "⟨kind⟩",
    "node.name": "⟨function⟩",
    "child.func.id": "⟨builtin⟩",
    "field": "⟨field⟩",
    "item.name": "⟨method⟩",
    "leaf": "⟨scalar⟩",
    "head": "⟨scalar⟩",
    "named": "⟨types⟩",
}

APPLIES_TO: Final[dict[str, str]] = {
    "Codebase.__init__": "checked source file",
    "Codebase.violations": "ignore comment",
    "Codebase._declaration_violations": "the checked tree itself",
    "Codebase._export_declaration_violations": "the checked tree itself",
    "Codebase._import_declaration_violations": "the checked tree itself",
    "Codebase._unused_import_violations": "the checked tree itself",
    "Codebase._kernel_init_violations": "kernel `__init__`",
    "Codebase._kernel_module_violations": "kernel module",
    "Codebase._kernel_import_violations": "kernel module",
    "Codebase._comment_violations": "every module",
    "Codebase._double_violations": "every module",
    "Codebase._shadowing_violations": "every module",
    "Codebase._string_equality_violations": "every module",
    "Codebase._vo_field_violations": "value object class",
    "Codebase._exposure_violations": "value object class",
    "Codebase._composition_violations": "value object class",
    "Codebase._door_violations": "value object class",
    "Codebase._exit_violations": "value object conversion dunder",
    "Codebase._structured_exit_violations": "entity or aggregate conversion dunder",
    "Codebase._copy_violations": "entity or aggregate accessor",
    "Codebase._held_root_violations": "entity or aggregate field",
    "Codebase._domain_return_violations": "domain object public method",
    "a service method": "public service method",
    "a client method": "client protocol method",
    "a domain constructor": "aggregate or entity `__init__`",
    "an aggregate": "aggregate class",
    "an entity": "entity class",
    "an adapter": "repository or gateway method",
    "a port": "port protocol method",
    "a port method": "port protocol method",
    "ports": "ports module",
    "Codebase._delegation_violations": "every service method, including private",
    "Codebase._body_violations": "public service method",
    "Codebase._module_violations": "context package",
    "Codebase._context_init_violations": "context `__init__`",
    "Codebase._dynamic_import_violations": "every module",
    "Codebase._ports_init_violations": "ports `__init__`",
    "Codebase._decoration_violations": "ports module",
    "Codebase._ports_shape_violations": "ports module",
    "Codebase._ports_call_shape": "ports module",
    "Codebase._unreadable": "ports module",
    "Codebase._ports_module_violations": "ports module",
    "Codebase._port_violations": "port protocol method",
    "Codebase._port_annotation_violations": "port protocol method",
    "Codebase._role_module_violations": "context role module",
    "Codebase._import_violations": "context role module",
    "Codebase._app_import_violations": "srv / bootstrap module",
    "Codebase._test_module_violations": "test module",
    "Codebase._test_placement_violations": "test module, by where it is placed",
    "Codebase._eval_module_violations": "eval module (`eval_*.py`)",
    "Codebase._context_tests_init_violations": "context tests `__init__`",
    "Codebase._homeless_violations": "top-level module",
    "Codebase._conftest_leaf_violations": "conftest module",
    "Codebase._shell_reach_violations": "test module, by where it is placed",
    "Codebase._tests_package_violations": "tests package module",
    "Codebase._role_init_violations": "role package `__init__`",
    "Codebase._app_init_violations": "srv / bootstrap `__init__`",
    "Codebase._protocol_init_violations": "protocol package `__init__`",
    "Codebase._bootstrap_module_violations": "bootstrap module",
    "Codebase._srv_module_violations": "srv module",
    "Codebase._protocol_module_violations": "protocol module",
    "srv": "srv module",
    "bootstrap": "bootstrap module",
    "protocol": "protocol module",
    "role": "context role module",
    "module": "context role module",
    "kernel": "kernel module",
    "test": "test module",
    "Codebase._form_violations": "direction-legal context import (role modules and their __init__, srv/bootstrap, test modules)",
    "Codebase._stray_import_violations": "role, srv/bootstrap, or test module",
    "Codebase._helper_violations": "@ts.helper function",
    "Codebase._pairing_violations": "implementation module and its sibling test file",
    "Codebase._dependency_violations": "service `__init__`",
    "Codebase._valueobject_violations": "value object `__init__`",
    "Codebase._spec_violations": "spec class",
    "Codebase._dto_violations": "request/response DTO",
}

WHERE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^(?:⟨[^⟩]+⟩[.:]*)+\s*")


class RuleRow(ts.ValueObject):

    _clause: checks.Text
    _code: checks.Code
    _applies_to: checks.Text
    _shapes: tuple[checks.Text, ...]
    _linenos: tuple[checks.Line, ...]

    def __init__(
        self,
        clause: str,
        code: str,
        applies_to: str,
        shapes: tuple[str, ...],
        linenos: tuple[int, ...],
    ) -> None:
        object.__setattr__(self, "_clause", checks.Text(clause))
        object.__setattr__(self, "_code", checks.Code(code))
        object.__setattr__(self, "_applies_to", checks.Text(applies_to))
        object.__setattr__(
            self, "_shapes", tuple(checks.Text(shape) for shape in shapes)
        )
        object.__setattr__(
            self, "_linenos", tuple(checks.Line(line) for line in linenos)
        )

    def clause(self) -> checks.Text:
        return self._clause

    def code(self) -> checks.Code:
        return self._code

    def applies_to(self) -> checks.Text:
        return self._applies_to

    def shapes(self) -> tuple[checks.Text, ...]:
        return self._shapes

    def linenos(self) -> tuple[checks.Line, ...]:
        return self._linenos


@ts.function
def _ts_name_map(tree: ast.Module) -> dict[str, str]:
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "TS_NAME_BY_BLOCK"
            and isinstance(node.value, ast.Dict)
        ):
            out: dict[str, str] = {}
            for key, value in zip(node.value.keys, node.value.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    out[key.value] = value.value
            return out
    raise RuntimeError("TS_NAME_BY_BLOCK not found in checks.py")


@ts.function
def _instantiations(
    tree: ast.Module, method: ast.FunctionDef
) -> list[dict[str, str | None]]:
    params = [arg.arg for arg in method.args.args if arg.arg != "self"]
    found: list[dict[str, str | None]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method.name
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
        ):
            binding: dict[str, str | None] = {}
            for name, arg in zip(params, node.args):
                if isinstance(arg, ast.Constant) and (
                    arg.value is None or isinstance(arg.value, str)
                ):
                    binding[name] = arg.value
            if binding not in found:
                found.append(binding)
    return found or [{}]


@ts.function
def _local_aliases(method: ast.FunctionDef) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in method.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Subscript)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "TS_NAME_BY_BLOCK"
            and isinstance(node.value.slice, ast.Name)
        ):
            out[node.targets[0].id] = node.value.slice.id
    return out


@ts.function
def _fill_hole(
    expr: ast.expr,
    binding: dict[str, str | None],
    aliases: dict[str, str],
    ts_map: dict[str, str],
    lineno: int,
) -> str | None:
    text = ast.unparse(expr)
    if isinstance(expr, ast.Name) and expr.id in binding:
        bound = binding[expr.id]
        if bound is None:
            return None
        return bound
    if text in HOLE_NAMES:
        return HOLE_NAMES[text]
    param: str | None = None
    if isinstance(expr, ast.Name) and expr.id in aliases:
        param = aliases[expr.id]
    elif (
        isinstance(expr, ast.Subscript)
        and isinstance(expr.value, ast.Name)
        and expr.value.id == "TS_NAME_BY_BLOCK"
        and isinstance(expr.slice, ast.Name)
    ):
        param = expr.slice.id
    if param is not None:
        if param not in binding:
            raise RuntimeError(
                f"checks.py:{lineno}: hole {{{text}}} depends on caller argument {param!r} that is not a literal"
            )
        block = binding[param]
        if block is None:
            return None
        return ts_map[block]
    raise RuntimeError(
        f"checks.py:{lineno}: no reader name for message hole {{{text}}}; extend HOLE_NAMES"
    )


@ts.function
def _render_message(
    node: ast.expr,
    binding: dict[str, str | None],
    aliases: dict[str, str],
    ts_map: dict[str, str],
    lineno: int,
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return str(node.value)
    if not isinstance(node, ast.JoinedStr):
        raise RuntimeError(
            f"checks.py:{lineno}: violation message is not a literal or f-string"
        )
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
            continue
        assert isinstance(value, ast.FormattedValue)
        filled = _fill_hole(value.value, binding, aliases, ts_map, lineno)
        if filled is None:
            return None
        parts.append(filled)
    return "".join(parts)


@ts.function
def _protocol_package(tree: ast.Module) -> str:
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PROTOCOL_PACKAGE"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return str(node.value.value)
    raise RuntimeError("PROTOCOL_PACKAGE not found in checks.py")


@ts.function
def rule_rows(tree: ast.Module) -> tuple[RuleRow, ...]:
    ts_map = _ts_name_map(tree)
    order: list[str] = []
    codes: dict[str, str] = {}
    applies: dict[str, str] = {}
    shapes: dict[str, list[str]] = {}
    linenos: dict[str, list[int]] = {}
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for method in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            calls = [
                node
                for node in ast.walk(method)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Violation"
            ]
            if not calls:
                continue
            aliases = _local_aliases(method)
            for binding in _instantiations(tree, method):
                for call in calls:
                    if call.keywords or len(call.args) != 4:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: Violation takes exactly the four "
                            "positional arguments (path, line, code, message)"
                        )
                    code_expr = call.args[2]
                    if isinstance(code_expr, ast.Constant) and isinstance(
                        code_expr.value, str
                    ):
                        code: str | None = code_expr.value
                    elif isinstance(code_expr, ast.Name) and code_expr.id in binding:
                        code = binding[code_expr.id]
                    else:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: violation code is neither a literal nor a "
                            "literally-bound parameter"
                        )
                    if code is None:
                        continue
                    message = _render_message(
                        call.args[3], binding, aliases, ts_map, call.lineno
                    )
                    if message is None:
                        continue
                    if "; " not in message:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: violation message lacks a '; <normative clause>' tail"
                        )
                    head, clause = message.rsplit("; ", 1)
                    if "⟨" in clause:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: the normative clause after ';' is not a literal"
                        )
                    shape = WHERE_PREFIX.sub("", head)
                    subject = binding.get("subject")
                    key = (
                        subject
                        if isinstance(subject, str)
                        else f"{cls.name}.{method.name}"
                    )
                    if key not in APPLIES_TO:
                        raise RuntimeError(
                            f"no APPLIES_TO entry for {key!r}; extend the map"
                        )
                    if clause not in codes:
                        order.append(clause)
                        codes[clause] = code
                        applies[clause] = APPLIES_TO[key]
                        shapes[clause] = []
                        linenos[clause] = []
                    if codes[clause] != code:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: clause {clause!r} carries code {code}, "
                            f"but an earlier site carries {codes[clause]}; one clause has one code"
                        )
                    if shape not in shapes[clause]:
                        shapes[clause].append(shape)
                    if call.lineno not in linenos[clause]:
                        linenos[clause].append(call.lineno)
    return tuple(
        RuleRow(
            clause,
            codes[clause],
            applies[clause],
            tuple(shapes[clause]),
            tuple(linenos[clause]),
        )
        for clause in order
    )


@ts.function
def test_assertions(
    modules: tuple[tuple[str, str], ...] = (),
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    out: list[tuple[str, tuple[str, ...]]] = []
    for _, text in modules:
        tree = ast.parse(text)
        for fn in tree.body:
            if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
                continue
            literals: list[str] = []
            for node in ast.walk(fn):
                if isinstance(node, ast.Assert):
                    for sub in ast.walk(node):
                        if (
                            isinstance(sub, ast.Constant)
                            and isinstance(sub.value, str)
                            and len(sub.value) >= 8
                        ):
                            literals.append(sub.value)
            out.append((fn.name, tuple(literals)))
    return tuple(out)


@ts.function
def covering_tests(
    clause: str, assertions: tuple[tuple[str, tuple[str, ...]], ...] = ()
) -> tuple[str, ...]:
    return tuple(
        name
        for name, literals in assertions
        if any(clause in literal for literal in literals)
    )


@ts.function
def contracts(text: str) -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    contract_id = None
    for line in text.splitlines():
        header = re.match(r"\[importlinter:contract:(.+)\]", line.strip())
        if header:
            contract_id = header.group(1)
            continue
        name = re.match(r"name\s*=\s*(.+)", line.strip())
        if name and contract_id is not None:
            found.append((contract_id, name.group(1)))
            contract_id = None
    return tuple(found)


@ts.function
def render(
    checks_text: str,
    test_modules: tuple[tuple[str, str], ...] = (),
    contracts_text: str = "",
) -> str:
    tree = ast.parse(checks_text)
    assertions = test_assertions(test_modules)
    lines = [
        "# Rules implemented in the spike",
        "",
        "Generated from the implementation by the rulebook — never hand-edit.",
        "`python3 -m srv.cli.rules --check` fails when this file drifts from the",
        "code; regenerate with `python3 -m srv.cli.rules`. One row per rule: the",
        "normative clause every violation message ends",
        "with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is",
        "exact: a test covers a rule when an assert literal contains the clause.",
        "",
        "## tessercheck rules (from the violation messages in tessercheck/domain/checks.py)",
        "",
        "| Code | The rule | Applies to | Fires when | Source | Fixtures |",
        "|---|---|---|---|---|---|",
    ]
    for row in rule_rows(tree):
        covered = covering_tests(str(row.clause()), assertions)
        coverage = ", ".join(covered) if covered else "NONE"
        shapes = " · ".join(str(shape) for shape in row.shapes()).replace("|", "\\|")
        source = "domain/checks.py:" + ",".join(
            str(int(line)) for line in sorted(row.linenos(), key=int)
        )
        lines.append(
            f"| {row.code()} | {row.clause()} | {row.applies_to()} | {shapes} | {source} | {coverage} |"
        )
    package = _protocol_package(tree)
    lines += [
        "",
        "## Named exemptions (carve-outs the code makes on purpose, not rules)",
        "",
        f"- modules under the top-level `{package}/` package are the protocol",
        "  modules (PROTOCOL_PACKAGE in tessercheck/domain/checks.py) — package membership",
        "  is the declaration; no suffix opts a module in, so a stray `*wire.py`",
        "  is homeless.",
        "- srv and protocol kinds carry placement and import rules only — no",
        "  signature or body rules yet (deliberate: the srv signature matrix",
        "  ruled the kinds and their invariants, not tessercheck rules over",
        "  their members — see TODOS.md).",
        "",
        "## Import contracts (from .importlinter)",
        "",
        "| Contract | Rule |",
        "|---|---|",
    ]
    for contract_id, name in contracts(contracts_text):
        lines.append(f"| {contract_id} | {name} |")
    lines += [
        "",
        "Import contracts are verified by violation-injection runs during development;",
        "no committed test re-runs them (named gap — cf. python-app's committed",
        "architecture violation-injection test).",
        "",
    ]
    return "\n".join(lines)
