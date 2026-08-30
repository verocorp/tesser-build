from __future__ import annotations

import ast
import re
import typing

import tesser.domain as ts

import tessercheck.domain.checks as checks

HOLE_NAMES: typing.Final[dict[str, str]] = {
    "where": "⟨module.Class.method⟩",
    "module.name()": "⟨module⟩",
    "cls.name": "⟨class⟩",
    "callee.attr": "⟨method⟩",
    "callee.id": "⟨function⟩",
    "len(params)": "⟨count⟩",
    "len(ports)": "⟨count⟩",
    "len(stores)": "⟨count⟩",
    "len(bases)": "⟨count⟩",
    "len(protocols)": "⟨count⟩",
    "len(held)": "⟨count⟩",
    "len(responses)": "⟨count⟩",
    "len(calls)": "⟨count⟩",
    "published": "⟨attribute⟩",
    "target.attr": "⟨attribute⟩",
    "node.func.value.attr": "⟨attribute⟩",
    "len(taken)": "⟨count⟩",
    "arg.arg": "⟨name⟩",
    "inner.attr": "⟨field⟩",
    "node.value": "⟨literal⟩",
    "stmt.name": "⟨name⟩",
    "node.name": "⟨class⟩",
    "member.name": "⟨method⟩",
    "sibling": "⟨method⟩",
    "inner.name": "⟨class⟩",
    "type(node).__name__": "⟨node⟩",
    "target": "⟨import⟩",
    "package": "⟨package⟩",
    "self._export": "⟨export⟩",
    "', '.join(outsiders)": "⟨packages⟩",
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
    "spec_name": "⟨name⟩",
    "shared_class": "⟨class⟩",
    "spec_label": "⟨spec⟩",
    "owner_label": "⟨class⟩",
    "target_name": "⟨class⟩",
    "supers": "⟨count⟩",
    "len(inits)": "⟨count⟩",
    "outcome": "⟨outcome⟩",
    "kept": "⟨field⟩",
    "taker": "⟨function⟩",
    "sunder": "⟨attribute⟩",
    "keyword": "⟨keyword⟩",
    "member": "⟨member⟩",
    "self._module": "⟨module⟩",
    "self._name": "⟨class⟩",
    "field.name()": "⟨field⟩",
    "method.name()": "⟨method⟩",
    "arg": "⟨name⟩",
    "decl.module()": "⟨module⟩",
    "decl.name()": "⟨class⟩",
    "delegate": "⟨method⟩",
    "function": "⟨function⟩",
    "owner": "⟨module⟩.⟨class⟩",
    "module_name": "⟨module⟩",
}

APPLIES_TO: typing.Final[dict[str, str]] = {
    "Codebase.__init__": "checked source file",
    "Codebase.violations": "debt marker",
    "Codebase._declaration_violations": "the checked tree itself",
    "Codebase._export_declaration_violations": "the checked tree itself",
    "Codebase._import_declaration_violations": "the checked tree itself",
    "Codebase._unused_import_violations": "the checked tree itself",
    "Codebase._stdlib_declaration_violations": "the checked tree itself",
    "Codebase._kernel_init_violations": "kernel `__init__`",
    "Codebase._kernel_module_violations": "kernel module",
    "Codebase._tesser_init_violations": "tesser distribution `__init__`",
    "Codebase._tesser_shell_violations": "tesser distribution module",
    "Codebase._kernel_import_violations": "kernel module",
    "Module.comment_violations": "every module",
    "Module.double_violations": "every module",
    "Module.shadowing_violations": "every module",
    "Module.string_equality_violations": "every module",
    "Module.sibling_reference_violations": "every class, in every module",
    "Codebase._spec_use_violations": "every function that holds a spec, in every module",
    "Codebase._spec_shared_violations": "domain object `__init__`",
    "ClassDecl.vo_field_violations": "value object class",
    "ClassDecl.exposure_violations": "value object class",
    "ClassDecl.composition_violations": "value object class",
    "ClassDecl.construction_path_violations": "value object class",
    "ClassDecl.exit_violations": "value object conversion dunder",
    "ClassDecl.structured_exit_violations": "entity or aggregate conversion dunder",
    "ClassDecl.copy_violations": "entity or aggregate accessor",
    "ClassDecl.held_root_violations": "entity or aggregate field",
    "ClassDecl.domain_method_violations": "domain object public method",
    "ClassDecl.outcome_violations": "outcome class",
    "ClassDecl.outcome_field_violations": "domain object field",
    "Module.outcome_use_violations": "every non-test module",
    "a service method": "public service method",
    "an actions method": "public actions method",
    "an orchestrator method": "public orchestrator method",
    "an application client method": "application client protocol method",
    "a service": "service `__init__`",
    "a class of actions": "actions `__init__`",
    "an orchestrator": "orchestrator `__init__`",
    "an application client package": "application client `__init__`",
    "an orchestrators package": "orchestrators `__init__`",
    "application client": "application client module",
    "a client method": "client protocol method",
    "a domain constructor": "aggregate or entity `__init__`",
    "a config constructor": "config `__init__`",
    "an aggregate": "aggregate class",
    "an entity": "entity class",
    "a config": "config class",
    "an adapter": "repository or gateway method",
    "a port": "port protocol method",
    "a port method": "port protocol method",
    "ports": "ports module",
    "Body.delegation_violations": "every service method, including private",
    "Body.violations": "public service method",
    "Codebase._module_violations": "context package",
    "Codebase._context_init_violations": "context `__init__`",
    "Module.dynamic_import_violations": "every module",
    "Codebase._ports_init_violations": "ports `__init__`",
    "Codebase._decoration_violations": "ports module",
    "Codebase._ports_shape_violations": "ports module",
    "Codebase._ports_call_shape": "ports module",
    "Codebase._unreadable": "ports module",
    "Codebase._ports_module_violations": "ports module",
    "ClassDecl.port_violations": "port protocol method",
    "Codebase._application_client_module_violations": "application client module",
    "Codebase._import_time_violations": "application client class",
    "Codebase._orchestrators_module_violations": "orchestrators module",
    "ClassDecl.actions_violations": "actions class",
    "ClassDecl.orchestrator_violations": "orchestrator class",
    "ClassDecl.actions_client_violations": "application client protocol method",
    "Body.port_call_violations": "public actions method",
    "Body.thread_violations": "public orchestrator method",
    "Body.held_context_violations": "repository or gateway class",
    "ClassDecl.store_violations": "store protocol method",
    "Codebase._role_module_violations": "context role module",
    "Codebase._import_violations": "context role module",
    "Codebase._app_import_violations": "srv / app module",
    "Codebase._test_module_violations": "test module",
    "Codebase._test_placement_violations": "test module, by where it is placed",
    "Codebase._eval_module_violations": "eval module (`eval_*.py`)",
    "Codebase._context_tests_init_violations": "context tests `__init__`",
    "Codebase._homeless_violations": "top-level module",
    "Codebase._conftest_leaf_violations": "conftest module",
    "Codebase._shell_reach_violations": "test module, by where it is placed",
    "Codebase._tests_package_violations": "tests package module",
    "Codebase._role_init_violations": "role package `__init__`",
    "Codebase._app_init_violations": "srv / app `__init__`",
    "Codebase._protocol_init_violations": "protocol package `__init__`",
    "Codebase._app_module_violations": "app module",
    "Codebase._srv_module_violations": "srv module",
    "Codebase._protocol_module_violations": "protocol module",
    "srv": "srv module",
    "app": "app module",
    "protocol": "protocol module",
    "role": "context role module",
    "module": "context role module",
    "context role": "context role module",
    "kernel": "kernel module",
    "test": "test module",
    "Codebase._form_violations": "direction-legal context import (role modules and their __init__, srv/app, test modules)",
    "ImportEdge.member_form_violations": "every import in every governed module",
    "Module.stray_import_violations": "role, srv/app, or test module",
    "Codebase._helper_violations": "@ts.helper function",
    "Codebase._pairing_violations": "implementation module and its sibling test file",
    "Codebase._valueobject_violations": "value object `__init__`",
    "ClassDecl.component_violations": "component class",
    "Codebase._mapper_violations": "mapper class",
    "Codebase._spec_violations": "spec class",
    "Codebase._dto_violations": "request/response DTO",
}

WHERE_PREFIX: typing.Final[re.Pattern[str]] = re.compile(r"^(?:⟨[^⟩]+⟩[.:]*)+\s*")

VIOLATION_SPEC: typing.Final[str] = "ViolationSpec"

VIOLATION_FIELDS: typing.Final[tuple[str, ...]] = ("path", "line", "code", "message")


class RuleRowSpec(ts.Spec):

    def __init__(
        self,
        clause: str,
        code: str,
        applies_to: str,
        shapes: tuple[str, ...],
        linenos: tuple[int, ...],
    ) -> None:
        self.clause = clause
        self.code = code
        self.applies_to = applies_to
        self.shapes = shapes
        self.linenos = linenos


class RuleRow(ts.ValueObject):

    _clause: checks.Text
    _code: checks.Code
    _applies_to: checks.Text
    _shapes: tuple[checks.Text, ...]
    _linenos: tuple[checks.Line, ...]

    def __init__(self, spec: RuleRowSpec) -> None:
        object.__setattr__(self, "_clause", checks.Text(spec.clause))
        object.__setattr__(self, "_code", checks.Code(spec.code))
        object.__setattr__(self, "_applies_to", checks.Text(spec.applies_to))
        object.__setattr__(
            self, "_shapes", tuple(checks.Text(shape) for shape in spec.shapes)
        )
        object.__setattr__(
            self, "_linenos", tuple(checks.Line(line) for line in spec.linenos)
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


def render(  # tesser:debt TB051
    checks_text: str,
    test_modules: tuple[tuple[str, str], ...] = (),
    contracts_text: str = "",
) -> str:
    def spec_fields(call: ast.Call) -> dict[str, ast.expr] | None:
        if call.keywords or len(call.args) != 1:
            return None
        spec = call.args[0]
        if not isinstance(spec, ast.Call):
            return None
        if isinstance(spec.func, ast.Name):
            named = spec.func.id
        elif isinstance(spec.func, ast.Attribute):
            named = spec.func.attr
        else:
            return None
        if named != VIOLATION_SPEC or len(spec.args) > len(VIOLATION_FIELDS):
            return None
        bound = dict(zip(VIOLATION_FIELDS, spec.args))
        for keyword in spec.keywords:
            if keyword.arg is None or keyword.arg in bound:
                return None
            bound[keyword.arg] = keyword.value
        if set(bound) != set(VIOLATION_FIELDS):
            return None
        return bound

    tree = ast.parse(checks_text)
    assertions: list[tuple[str, tuple[str, ...]]] = []
    for _, module_text in test_modules:
        module_tree = ast.parse(module_text)
        for fn in module_tree.body:
            if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
                continue
            literals: list[str] = []
            for assert_node in ast.walk(fn):
                if isinstance(assert_node, ast.Assert):
                    for sub in ast.walk(assert_node):
                        if (
                            isinstance(sub, ast.Constant)
                            and isinstance(sub.value, str)
                            and len(sub.value) >= 8
                        ):
                            literals.append(sub.value)
            assertions.append((fn.name, tuple(literals)))
    ts_map: dict[str, str] | None = None
    for ts_node in tree.body:
        if (
            isinstance(ts_node, ast.AnnAssign)
            and isinstance(ts_node.target, ast.Name)
            and ts_node.target.id == "TS_NAME_BY_BLOCK"
            and isinstance(ts_node.value, ast.Dict)
        ):
            ts_map = {}
            for ts_key, ts_value in zip(ts_node.value.keys, ts_node.value.values):
                if (
                    isinstance(ts_key, ast.Constant)
                    and isinstance(ts_key.value, str)
                    and isinstance(ts_value, ast.Constant)
                    and isinstance(ts_value.value, str)
                ):
                    ts_map[ts_key.value] = ts_value.value
            break
    if ts_map is None:
        raise RuntimeError("TS_NAME_BY_BLOCK not found in checks.py")
    order: list[str] = []
    codes: dict[str, str] = {}
    applies: dict[str, list[str]] = {}
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
            aliases: dict[str, str] = {}
            for alias_node in method.body:
                if (
                    isinstance(alias_node, ast.Assign)
                    and len(alias_node.targets) == 1
                    and isinstance(alias_node.targets[0], ast.Name)
                    and isinstance(alias_node.value, ast.Subscript)
                    and isinstance(alias_node.value.value, ast.Name)
                    and alias_node.value.value.id == "TS_NAME_BY_BLOCK"
                    and isinstance(alias_node.value.slice, ast.Name)
                ):
                    aliases[alias_node.targets[0].id] = alias_node.value.slice.id
            params = [arg.arg for arg in method.args.args if arg.arg != "self"]
            bindings: list[dict[str, str | None]] = []
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == method.name
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"
                ):
                    bound_args: dict[str, str | None] = {}
                    for name, arg in zip(params, node.args):
                        if isinstance(arg, ast.Constant) and (
                            arg.value is None or isinstance(arg.value, str)
                        ):
                            bound_args[name] = arg.value
                    if bound_args not in bindings:
                        bindings.append(bound_args)
            spec_names: list[str] = []
            for member in cls.body:
                if isinstance(member, ast.FunctionDef) and member.name == "__init__":
                    for spec_arg in member.args.args[1:]:
                        if isinstance(spec_arg.annotation, ast.Name) and spec_arg.annotation.id.endswith("Spec"):
                            spec_names.append(spec_arg.annotation.id)
            for spec_name in spec_names:
                spec_cls = next(
                    (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == spec_name), None
                )
                spec_init = next(
                    (m for m in spec_cls.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
                    None,
                ) if spec_cls is not None else None
                if spec_init is None:
                    continue
                spec_params = [a.arg for a in spec_init.args.args[1:]]
                defaulted = spec_params[len(spec_params) - len(spec_init.args.defaults):]
                for node in ast.walk(tree):
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == spec_name
                    ):
                        continue
                    spec_bound: dict[str, str | None] = {}
                    for name, default in zip(defaulted, spec_init.args.defaults):
                        if isinstance(default, ast.Constant) and (
                            default.value is None or isinstance(default.value, str)
                        ):
                            spec_bound[name] = default.value
                    for name, arg in zip(spec_params, node.args):
                        if isinstance(arg, ast.Constant) and (arg.value is None or isinstance(arg.value, str)):
                            spec_bound[name] = arg.value
                    for keyword in node.keywords:
                        if (
                            keyword.arg is not None
                            and isinstance(keyword.value, ast.Constant)
                            and (keyword.value.value is None or isinstance(keyword.value.value, str))
                        ):
                            spec_bound[keyword.arg] = keyword.value.value
                    if spec_bound not in bindings:
                        bindings.append(spec_bound)
            for binding in bindings or [{}]:
                for call in calls:
                    fields = spec_fields(call)
                    if fields is None:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: Violation takes exactly the four "
                            "spec fields (path, line, code, message), as one ViolationSpec"
                        )
                    code_expr = fields["code"]
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
                    used: list[str] = []
                    message_node = fields["message"]
                    if isinstance(message_node, ast.Constant) and isinstance(
                        message_node.value, str
                    ):
                        message = str(message_node.value)
                    else:
                        if not isinstance(message_node, ast.JoinedStr):
                            raise RuntimeError(
                                f"checks.py:{call.lineno}: violation message is not a literal or f-string"
                            )
                        parts: list[str] = []
                        dropped = False
                        for value in message_node.values:
                            if isinstance(value, ast.Constant) and isinstance(
                                value.value, str
                            ):
                                parts.append(value.value)
                                continue
                            assert isinstance(value, ast.FormattedValue)
                            expr = value.value
                            text = ast.unparse(expr)
                            if isinstance(expr, ast.Name) and expr.id in binding:
                                bound = binding[expr.id]
                                used.append(expr.id)
                                if bound is None or bound == "":
                                    dropped = True
                                    break
                                parts.append(bound)
                                continue
                            if text in HOLE_NAMES:
                                parts.append(HOLE_NAMES[text])
                                continue
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
                            if param is None:
                                raise RuntimeError(
                                    f"checks.py:{call.lineno}: no reader name for message hole {{{text}}}; extend HOLE_NAMES"
                                )
                            if param not in binding:
                                raise RuntimeError(
                                    f"checks.py:{call.lineno}: hole {{{text}}} depends on caller argument {param!r} that is not a literal"
                                )
                            block = binding[param]
                            if block is None:
                                dropped = True
                                break
                            parts.append(ts_map[block])
                        if dropped:
                            continue
                        message = "".join(parts)
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
                    named_subject = next(
                        (binding[name] for name in used if isinstance(binding.get(name), str) and binding[name] in APPLIES_TO),
                        None,
                    )
                    key = (
                        named_subject
                        if isinstance(named_subject, str)
                        else subject
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
                        applies[clause] = []
                        shapes[clause] = []
                        linenos[clause] = []
                    if codes[clause] != code:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: clause {clause!r} carries code {code}, "
                            f"but an earlier site carries {codes[clause]}; one clause has one code"
                        )
                    if APPLIES_TO[key] not in applies[clause]:
                        applies[clause].append(APPLIES_TO[key])
                    if shape not in shapes[clause]:
                        shapes[clause].append(shape)
                    if call.lineno not in linenos[clause]:
                        linenos[clause].append(call.lineno)
    lines = [
        "# Rules implemented in the spike",
        "",
        "Generated from the implementation by the rulebook — never hand-edit.",
        "`python3 -m srv.cli.rules --check` fails when this file drifts from the",
        "code; regenerate with `python3 -m srv.cli.rules`. One row per rule: the",
        "normative clause every violation message ends with. ⟨…⟩ marks a value",
        "filled in per violation. A rule emitted from more than one owner lists",
        "every owner in Applies to, joined by ·. Fixture coverage is exact: a",
        "test covers a rule when an assert literal contains the clause.",
        "",
        "## tessercheck rules (from the violation messages in tessercheck/domain/checks.py)",
        "",
        "| Code | The rule | Applies to | Fires when | Source | Fixtures |",
        "|---|---|---|---|---|---|",
    ]
    for row in (
        RuleRow(
            RuleRowSpec(
                clause,
                codes[clause],
                " · ".join(applies[clause]),
                tuple(shapes[clause]),
                tuple(linenos[clause]),
            )
        )
        for clause in order
    ):
        covered = tuple(
            name
            for name, literals in assertions
            if any(str(row.clause()) in literal for literal in literals)
        )
        coverage = ", ".join(covered) if covered else "NONE"
        shape_text = " · ".join(str(shape) for shape in row.shapes()).replace("|", "\\|")
        source = "domain/checks.py:" + ",".join(
            str(int(line)) for line in sorted(row.linenos(), key=int)
        )
        lines.append(
            f"| {row.code()} | {row.clause()} | {row.applies_to()} | {shape_text} | {source} | {coverage} |"
        )
    package: str | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PROTOCOL_PACKAGE"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            package = str(node.value.value)
            break
    if package is None:
        raise RuntimeError("PROTOCOL_PACKAGE not found in checks.py")
    lines += [
        "",
        "## Named exemptions (carve-outs the code makes on purpose, not rules)",
        "",
        f"- modules under the top-level `{package}/` package are the protocol",
        "  modules (PROTOCOL_PACKAGE in tessercheck/domain/checks.py) — package membership",
        "  is the declaration; no suffix opts a module in, so a stray `*wire.py`",
        "  is homeless.",
        "- the job kind (`ts.Job`, in `adapters/jobs/`) carries placement and",
        "  import rules only — no signature or body rules yet (deliberate: the",
        "  job's reach is what the split exists for; what a job may hold is a",
        "  later wave).",
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
    contract_id = None
    for contract_line in contracts_text.splitlines():
        header = re.match(r"\[importlinter:contract:(.+)\]", contract_line.strip())
        if header:
            contract_id = header.group(1)
            continue
        name_match = re.match(r"name\s*=\s*(.+)", contract_line.strip())
        if name_match and contract_id is not None:
            lines.append(f"| {contract_id} | {name_match.group(1)} |")
            contract_id = None
    lines += [
        "",
        "Import contracts are verified by violation-injection runs during development;",
        "no committed test re-runs them (named gap — cf. python-app's committed",
        "architecture violation-injection test).",
        "",
    ]
    return "\n".join(lines)
