import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DOMAIN = ROOT / "sigcheck" / "domain" / "checks.py"
TESTS = ROOT / "tests" / "test_sigcheck.py"
CONTRACTS = ROOT / ".importlinter"
OUTPUT = ROOT / "RULES.md"

HOLE_NAMES: dict[str, str] = {
    "where": "⟨module.Class.method⟩",
    "module.name()": "⟨module⟩",
    "cls.name": "⟨class⟩",
    "callee.attr": "⟨method⟩",
    "callee.id": "⟨function⟩",
    "len(params)": "⟨count⟩",
    "arg.arg": "⟨name⟩",
    "stmt.name": "⟨name⟩",
    "span": "⟨count⟩",
    "target": "⟨import⟩",
    "package": "⟨package⟩",
    "tier": "⟨tier⟩",
    "own_roles": "⟨roles⟩",
    "foreign_roles": "⟨roles⟩",
    "KIND_NAME[block]": "⟨kind⟩",
    "KIND_ROLE[block]": "⟨role⟩",
    "KIND_NAME[touched]": "⟨kind⟩",
    "name": "⟨module⟩",
    "others": "⟨paths⟩",
    "error.msg": "⟨error⟩",
}

APPLIES_TO: dict[str, str] = {
    "Codebase.__init__": "checked source file",
    "Codebase.violations": "ignore comment",
    "a service method": "public service method",
    "a client method": "client protocol method",
    "a domain constructor": "aggregate or entity `__init__`",
    "an aggregate": "aggregate class",
    "an entity": "entity class",
    "an adapter": "repository or gateway method",
    "a port": "port protocol method",
    "Codebase._delegation_violations": "every service method, including private",
    "Codebase._body_violations": "public service method",
    "Codebase._module_violations": "context package",
    "Codebase._context_init_violations": "context `__init__`",
    "Codebase._role_module_violations": "context role module",
    "Codebase._import_violations": "context role module",
    "Codebase._app_import_violations": "srv / bootstrap module",
    "Codebase._test_module_violations": "test module",
    "Codebase._test_placement_violations": "test module, by where it is placed",
    "Codebase._eval_module_violations": "eval module (`eval_*.py`)",
    "Codebase._context_tests_init_violations": "context tests `__init__`",
    "Codebase._homeless_violations": "top-level module",
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
    "test": "test module",
    "Codebase._form_violations": "direction-legal context import (role modules and their __init__, srv/bootstrap, test modules)",
    "Codebase._stray_import_violations": "role, srv/bootstrap, or test module",
    "Codebase._helper_violations": "@ts.helper function",
    "Codebase._dependency_violations": "service `__init__`",
    "Codebase._valueobject_violations": "value object `__init__`",
    "Codebase._spec_violations": "spec class",
    "Codebase._dto_violations": "request/response DTO",
}

WHERE_PREFIX = re.compile(r"^(?:⟨[^⟩]+⟩[.:]*)+\s*")


class RuleRow:

    def __init__(self, clause: str, code: str, applies_to: str) -> None:
        self.clause = clause
        self.code = code
        self.applies_to = applies_to
        self.shapes: list[str] = []
        self.linenos: list[int] = []

    def add(self, shape: str, lineno: int) -> None:
        if shape not in self.shapes:
            self.shapes.append(shape)
        if lineno not in self.linenos:
            self.linenos.append(lineno)


def ts_name_map(tree: ast.Module) -> dict[str, str]:
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


def instantiations(tree: ast.Module, method: ast.FunctionDef) -> list[dict[str, str | None]]:
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
                if isinstance(arg, ast.Constant) and (arg.value is None or isinstance(arg.value, str)):
                    binding[name] = arg.value
            if binding not in found:
                found.append(binding)
    return found or [{}]


def local_aliases(method: ast.FunctionDef) -> dict[str, str]:
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


def fill_hole(
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
    raise RuntimeError(f"checks.py:{lineno}: no reader name for message hole {{{text}}}; extend HOLE_NAMES")


def render_message(
    node: ast.expr,
    binding: dict[str, str | None],
    aliases: dict[str, str],
    ts_map: dict[str, str],
    lineno: int,
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.JoinedStr):
        raise RuntimeError(f"checks.py:{lineno}: violation message is not a literal or f-string")
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
            continue
        assert isinstance(value, ast.FormattedValue)
        filled = fill_hole(value.value, binding, aliases, ts_map, lineno)
        if filled is None:
            return None
        parts.append(filled)
    return "".join(parts)


def protocol_package(tree: ast.Module) -> str:
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PROTOCOL_PACKAGE"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise RuntimeError("PROTOCOL_PACKAGE not found in checks.py")


def tooling_modules(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "TOOLING_MODULES"
        ):
            if (
                isinstance(node.value, ast.Call)
                and len(node.value.args) == 1
                and isinstance(node.value.args[0], ast.Set)
            ):
                return sorted(
                    element.value
                    for element in node.value.args[0].elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                )
            raise RuntimeError(
                "TOOLING_MODULES has an unexpected shape; expected frozenset({...}) of string literals"
            )
    raise RuntimeError("TOOLING_MODULES not found in checks.py")


UNGOVERNED_PROSE: dict[str, list[str]] = {
    "conftest": [
        "- a `conftest` module is ungoverned (kept for now — followup pending with",
        "  the test-organization work).",
    ],
    "__main__": [
        "- a context `__main__` is ungoverned (named ruling, PR #48).",
    ],
}


def ungoverned_basenames(tree: ast.Module) -> list[str]:
    """The basenames `_module_violations` exempts with an early `return ()`.

    Derived from the AST guards, so governing conftest (or `__main__`) forces
    the RULES.md diff instead of leaving a stale exemption bullet behind.
    """
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for method in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            if method.name != "_module_violations":
                continue
            found: list[str] = []
            for node in ast.walk(method):
                if not (
                    isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "basename"
                    and len(node.test.ops) == 1
                    and isinstance(node.test.ops[0], ast.Eq)
                    and len(node.test.comparators) == 1
                    and isinstance(node.test.comparators[0], ast.Constant)
                    and isinstance(node.test.comparators[0].value, str)
                ):
                    continue
                if (
                    len(node.body) == 1
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Tuple)
                    and not node.body[0].value.elts
                ):
                    found.append(node.test.comparators[0].value)
            return found
    raise RuntimeError("_module_violations not found in checks.py")


def ungoverned_bullets(tree: ast.Module) -> list[str]:
    derived = ungoverned_basenames(tree)
    if set(derived) != set(UNGOVERNED_PROSE):
        raise RuntimeError(
            f"ungoverned basenames in checks.py {sorted(derived)} do not match "
            f"UNGOVERNED_PROSE {sorted(UNGOVERNED_PROSE)}; update rules.py"
        )
    return [line for name in derived for line in UNGOVERNED_PROSE[name]]


def rule_rows(tree: ast.Module) -> list[RuleRow]:
    ts_map = ts_name_map(tree)
    rows: dict[str, RuleRow] = {}
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
            aliases = local_aliases(method)
            for binding in instantiations(tree, method):
                for call in calls:
                    if call.keywords or len(call.args) != 4:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: Violation takes exactly the four "
                            "positional arguments (path, line, code, message)"
                        )
                    code_expr = call.args[2]
                    if isinstance(code_expr, ast.Constant) and isinstance(code_expr.value, str):
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
                    message = render_message(call.args[3], binding, aliases, ts_map, call.lineno)
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
                    key = subject if isinstance(subject, str) else f"{cls.name}.{method.name}"
                    if key not in APPLIES_TO:
                        raise RuntimeError(f"no APPLIES_TO entry for {key!r}; extend the map")
                    row = rows.setdefault(clause, RuleRow(clause, code, APPLIES_TO[key]))
                    if row.code != code:
                        raise RuntimeError(
                            f"checks.py:{call.lineno}: clause {clause!r} carries code {code}, "
                            f"but an earlier site carries {row.code}; one clause has one code"
                        )
                    row.add(shape, call.lineno)
    return list(rows.values())


def test_assertions() -> dict[str, list[str]]:
    tree = ast.parse(TESTS.read_text())
    out: dict[str, list[str]] = {}
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
            continue
        literals: list[str] = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Assert):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and len(sub.value) >= 8:
                        literals.append(sub.value)
        out[fn.name] = literals
    return out


def covering_tests(clause: str, assertions: dict[str, list[str]]) -> list[str]:
    return [name for name, literals in assertions.items() if any(clause in literal for literal in literals)]


def contracts() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    contract_id = None
    for line in CONTRACTS.read_text().splitlines():
        header = re.match(r"\[importlinter:contract:(.+)\]", line.strip())
        if header:
            contract_id = header.group(1)
            continue
        name = re.match(r"name\s*=\s*(.+)", line.strip())
        if name and contract_id is not None:
            found.append((contract_id, name.group(1)))
            contract_id = None
    return found


def render() -> str:
    tree = ast.parse(DOMAIN.read_text())
    assertions = test_assertions()
    lines = [
        "# Rules implemented in the spike",
        "",
        "Generated from the implementation by `rules.py` — never hand-edit.",
        "`python3 rules.py --check` fails when this file drifts from the code.",
        "One row per rule: the normative clause every violation message ends",
        "with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is",
        "exact: a test covers a rule when an assert literal contains the clause.",
        "",
        "## sigcheck rules (from the violation messages in sigcheck/domain/checks.py)",
        "",
        "| Code | The rule | Applies to | Fires when | Source | Fixtures |",
        "|---|---|---|---|---|---|",
    ]
    for row in rule_rows(tree):
        covered = covering_tests(row.clause, assertions)
        coverage = ", ".join(covered) if covered else "NONE"
        shapes = " · ".join(row.shapes).replace("|", "\\|")
        source = "domain/checks.py:" + ",".join(str(n) for n in sorted(row.linenos))
        lines.append(
            f"| {row.code} | {row.clause} | {row.applies_to} | {shapes} | {source} | {coverage} |"
        )
    tooling = ", ".join(f"`{name}`" for name in tooling_modules(tree))
    package = protocol_package(tree)
    lines += [
        "",
        "## Named exemptions (carve-outs the code makes on purpose, not rules)",
        "",
        *ungoverned_bullets(tree),
        f"- tooling modules outside the taxonomy: {tooling} (TOOLING_MODULES in",
        "  sigcheck/domain/checks.py — the whole-tree totality rule skips them).",
        f"- modules under the top-level `{package}/` package are the protocol",
        "  modules (PROTOCOL_PACKAGE in sigcheck/domain/checks.py) — package membership",
        "  is the declaration; no suffix opts a module in, so a stray `*wire.py`",
        "  is homeless.",
        "- srv and protocol kinds carry placement and import rules only — no",
        "  signature or body rules yet (deliberate: the srv signature matrix",
        "  ruled the kinds and their invariants, not sigcheck rules over",
        "  their members — see TODOS.md).",
        "",
        "## Import contracts (from .importlinter)",
        "",
        "| Contract | Rule |",
        "|---|---|",
    ]
    for contract_id, name in contracts():
        lines.append(f"| {contract_id} | {name} |")
    lines += [
        "",
        "Import contracts are verified by violation-injection runs during development;",
        "no committed test re-runs them (named gap — cf. python-app's committed",
        "architecture violation-injection test).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rendered = render()
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print("RULES.md is stale; regenerate with: python3 rules.py")
            return 1
        print("RULES.md is current")
        return 0
    OUTPUT.write_text(rendered)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
