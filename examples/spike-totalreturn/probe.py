"""Probe for one proposed rule, measured rather than argued.

The rule under test, in its purest form:

    Every method on a domain object returns another domain object.
    No primitives. Not bool. Not an enum -- enums are primitives here.

This encodes that rule with ZERO licensed exits and runs it over the repo's
Python domain corpus, so "where it breaks" is a list of file:line rather than a
prediction. `main.go` in this directory is the same probe for the Go corpus;
it needs a Go toolchain, which this sandbox lacks.

A "domain object" is a class whose bases include ValueObject / Entity /
Aggregate (the tesser.domain runtime bases) -- all three, because the rule under
test is about all three.

Usage: python3 examples/spike-totalreturn/probe.py examples tesser-py
"""

from __future__ import annotations

import ast
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# The runtime bases that mark a class as a domain object. Matched on the
# attribute's last segment, so `ts.ValueObject` and a bare `ValueObject` both hit.
DOMAIN_BASES = frozenset({"ValueObject", "Entity", "Aggregate", "AggregateRoot"})

# Python builtins the proposal names as primitive outright.
BUILTINS = frozenset({"str", "int", "float", "bool", "bytes", "None", "NoneType", "complex"})

# Named types from outside the domain: real values, but nobody's domain object.
FOREIGN = frozenset({"Decimal", "datetime", "date", "time", "UUID", "Pattern", "timedelta"})

# Containers whose element type is what the rule is actually about.
CONTAINERS = frozenset({"tuple", "list", "set", "frozenset", "Sequence", "Mapping",
                        "Iterable", "Iterator", "dict", "Optional"})

# Dunders whose return type the LANGUAGE fixes, not the author. These are the
# rule's hard boundary: no amount of domain modelling can change what
# `__eq__` is allowed to return.
PROTOCOL_FIXED = {
    "__eq__": "bool", "__ne__": "bool", "__hash__": "int", "__bool__": "bool",
    "__str__": "str", "__repr__": "str", "__int__": "int", "__float__": "float",
    "__bytes__": "bytes", "__len__": "int", "__lt__": "bool", "__le__": "bool",
    "__gt__": "bool", "__ge__": "bool", "__contains__": "bool", "__format__": "str",
    "__init__": "None", "__setattr__": "None", "__delattr__": "None",
}

DOMAIN = "DOMAIN"
PRIMITIVE = "PRIMITIVE"
# COMMAND is a mutator returning nothing. It breaks the rule for a different
# reason than a leaking query does: there is no value to promote, only a
# choice between command-style and returning the new state.
COMMAND = "COMMAND"
ENUM = "ENUM"
FOREIGN_V = "FOREIGN"
UNKNOWN = "UNKNOWN"
# AMBIGUOUS: the same class name means different things in different modules.
# Reported rather than resolved -- guessing here is how the first draft of this
# probe classified arm_enum's LinkStatus(Enum) as DOMAIN.
AMBIGUOUS = "AMBIGUOUS"


@dataclass
class Finding:
    path: str
    line: int
    cls: str
    method: str
    annotation: str
    verdict: str
    # protocol is set when the language, not the author, fixes the return type.
    protocol: bool


def base_names(node: ast.ClassDef) -> set[str]:
    out = set()
    for b in node.bases:
        if isinstance(b, ast.Name):
            out.add(b.id)
        elif isinstance(b, ast.Attribute):
            out.add(b.attr)
    return out


def collect_types(roots: list[Path]):
    """Return (domain names by kind, per-module name->kind, global name->kinds, modules).

    Names are resolved per-module first. A bare-name registry is wrong: two
    modules may each define a `LinkStatus` -- one an enum, one a value object --
    and a module-blind lookup silently classifies the enum as DOMAIN. Where a
    name is not defined locally, it resolves globally only if unambiguous;
    otherwise it is reported rather than guessed.
    """
    domain: dict[str, set[str]] = {kind: set() for kind in sorted(DOMAIN_BASES)}
    per_module: dict[str, dict[str, str]] = {}
    global_kinds: dict[str, set[str]] = {}
    modules: list[tuple[Path, ast.Module]] = []
    for root in roots:
        for f in sorted(root.rglob("*.py")):
            if "test" in f.name or ".venv" in f.parts:
                continue
            # statearms/ holds deliberate anti-pattern fixtures. They are
            # measured by pointing the probe AT that directory, and skipped
            # when it is merely swept up in a corpus walk -- otherwise the
            # corpus tally counts fixtures as findings.
            if "statearms" in f.parts and root.name != "statearms":
                continue
            try:
                tree = ast.parse(f.read_text(), filename=str(f))
            except SyntaxError:
                continue
            modules.append((f, tree))
            local: dict[str, str] = {}
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = base_names(node)
                kind = ""
                if bases & DOMAIN_BASES:
                    kind = DOMAIN
                    for k in DOMAIN_BASES & bases:
                        domain[k].add(node.name)
                elif bases & {"Enum", "StrEnum", "IntEnum", "Flag"}:
                    kind = ENUM
                if kind:
                    local[node.name] = kind
                    global_kinds.setdefault(node.name, set()).add(kind)
            per_module[str(f)] = local
    return domain, per_module, global_kinds, modules


def annotation_text(node: ast.expr | None) -> str:
    if node is None:
        return "<unannotated>"
    return ast.unparse(node)


def classify(node: ast.expr | None, local: dict[str, str], glob: dict[str, set[str]]) -> str:
    """Classify a return annotation. Containers classify by element type.

    `local` is the defining module's own classes; `glob` is every class name
    seen, mapped to the set of kinds that name carries anywhere in the corpus.
    """
    domain, enums = local, glob
    if node is None:
        return UNKNOWN
    if isinstance(node, ast.Constant):
        if node.value is None:
            return PRIMITIVE
        if isinstance(node.value, str):  # a string-literal forward reference
            try:
                return classify(ast.parse(node.value, mode="eval").body, domain, enums)
            except SyntaxError:
                return UNKNOWN
    if isinstance(node, ast.Attribute):
        return classify(ast.Name(id=node.attr), domain, enums)
    if isinstance(node, ast.Subscript):
        head = node.value.id if isinstance(node.value, ast.Name) else getattr(node.value, "attr", "")
        if head in CONTAINERS:
            sl = node.slice
            elems = sl.elts if isinstance(sl, ast.Tuple) else [sl]
            # A Mapping's value type is the payload; a tuple[X, ...]'s is X.
            picks = [e for e in elems if not (isinstance(e, ast.Constant) and e.value is Ellipsis)]
            if head in {"Mapping", "dict"} and len(picks) == 2:
                picks = picks[1:]
            verdicts = {classify(e, domain, enums) for e in picks}
            return DOMAIN if verdicts == {DOMAIN} else sorted(verdicts)[0]
        return UNKNOWN
    if isinstance(node, ast.BinOp):  # X | None
        return classify(node.left, domain, enums)
    if isinstance(node, ast.Name):
        n = node.id
        if n == "Self":
            return DOMAIN
        # Local definitions win: the module you are reading is the module that
        # decided what this name means.
        if n in local:
            return local[n]
        if n in glob:
            kinds = glob[n]
            # Two modules disagree about this name. Say so; do not pick.
            return next(iter(kinds)) if len(kinds) == 1 else AMBIGUOUS
        if n in BUILTINS:
            return PRIMITIVE
        if n in FOREIGN:
            return FOREIGN_V
        return UNKNOWN
    return UNKNOWN


def measure(modules, per_module, global_kinds) -> list[Finding]:
    findings: list[Finding] = []
    for path, tree in modules:
        local = per_module.get(str(path), {})
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not (base_names(node) & DOMAIN_BASES):
                continue
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                verdict = classify(item.returns, local, global_kinds)
                if verdict == PRIMITIVE and annotation_text(item.returns) == "None":
                    verdict = COMMAND
                findings.append(Finding(
                    path=str(path), line=item.lineno, cls=node.name, method=item.name,
                    annotation=annotation_text(item.returns), verdict=verdict,
                    protocol=item.name in PROTOCOL_FIXED,
                ))
    return findings


def main() -> int:
    roots = [Path(a) for a in sys.argv[1:]] or [Path("examples"), Path("tesser-py")]
    domain_by_kind, per_module, global_kinds, modules = collect_types(roots)
    findings = measure(modules, per_module, global_kinds)

    breaks = [f for f in findings if f.verdict != DOMAIN]
    fixed = [f for f in breaks if f.protocol]
    # A private helper is not part of the type's contract; the rule is about the
    # public surface, so split it out rather than inflating the break list.
    authored = [f for f in breaks if not f.protocol and not f.method.startswith("_")]
    private = [f for f in breaks if not f.protocol and f.method.startswith("_")]

    print("=== A. UNSATISFIABLE: the language fixes these return types ===")
    print("    (no domain modelling can change them -- the rule cannot reach here)")
    for f in sorted({(f.cls, f.method, PROTOCOL_FIXED[f.method]) for f in fixed}):
        print(f"  {f[1]:<14} -> {f[2]:<6} on {f[0]}")
    print(f"  ... {len(fixed)} call sites across {len({f.cls for f in fixed})} domain classes")

    print("\n=== B. AUTHORED: methods the rule could actually force to change ===")
    for f in sorted(authored, key=lambda f: (f.path, f.line)):
        print(f"  {f.path}:{f.line}  {f.cls}.{f.method} -> {f.annotation}  [{f.verdict}]")

    print("\n=== TALLY ===")
    for kind, names in sorted(domain_by_kind.items()):
        print(f"  {kind:<12} classes: {len(names)}")
    print(f"  methods measured:     {len(findings)}")
    print(f"  conform already:      {len(findings) - len(breaks)}")
    print(f"  break, LANGUAGE-fixed:{len(fixed)}   <- rule is unsatisfiable here")
    print(f"  break, private helper:{len(private)}   <- out of contract, not the rule's business")
    print(f"  break, PUBLIC authored:{len(authored)}  <- the rule's real scope")
    print("  public breaks by verdict:", dict(Counter(f.verdict for f in authored)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
