import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DOMAIN = ROOT / "sigcheck" / "domain.py"
TESTS = ROOT / "tests" / "test_sigcheck.py"
CONTRACTS = ROOT / ".importlinter"
OUTPUT = ROOT / "RULES.md"
MATCH_THRESHOLD = 0.6


def flatten_template(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{…}")
        return "".join(parts)
    return None


def violation_templates() -> list[tuple[str, int, str]]:
    tree = ast.parse(DOMAIN.read_text())
    found: list[tuple[str, int, str]] = []
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for method in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            for node in ast.walk(method):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "Violation"
                    and node.args
                ):
                    template = flatten_template(node.args[0])
                    found.append(
                        (f"{cls.name}.{method.name}", node.lineno, template or "(unparsed message)")
                    )
    return found


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


def tokens(text: str) -> list[str]:
    text = re.sub(r"'[^']*'", " ", text)
    return re.sub(r"[^a-z]+", " ", text.lower()).split()


def covering_tests(template: str, assertions: dict[str, list[str]]) -> list[str]:
    template_tokens = set(tokens(template))
    names: list[str] = []
    for name, literals in assertions.items():
        for literal in literals:
            literal_tokens = tokens(literal)
            if not literal_tokens:
                continue
            hit = sum(1 for t in literal_tokens if t in template_tokens)
            if hit / len(literal_tokens) >= MATCH_THRESHOLD:
                names.append(name)
                break
    return names


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
    assertions = test_assertions()
    lines = [
        "# Rules implemented in the spike",
        "",
        "Generated from the implementation by `rules.py` — never hand-edit.",
        "`python3 rules.py --check` fails when this file drifts from the code.",
        "Fixture coverage is a token-overlap heuristic over test assertion strings.",
        "",
        "## sigcheck rules (from the violation messages in sigcheck/domain.py)",
        "",
        "| Family | Message template | Source line | Fixture coverage |",
        "|---|---|---|---|",
    ]
    for family, lineno, template in violation_templates():
        covered = covering_tests(template, assertions)
        coverage = ", ".join(covered) if covered else "NONE"
        shown = template.replace("|", "\\|")
        lines.append(f"| {family} | {shown} | domain.py:{lineno} | {coverage} |")
    lines += [
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
