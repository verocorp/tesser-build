"""The roadmap-matrix generator: emits ``roadmap/ROADMAP.md`` by scanning the
repo — the roadmap is a query the repo answers about itself, never a
hand-maintained table.

Derivation is deterministic and non-LLM (design 2026-07-18, Wave 2 item 10):

- **Row taxonomy** comes from ``roadmap/registry.json`` (eng review D11b) —
  never from constants in this file.
- **Mechanical cells** are computed: skill-file presence + ``tb-status``
  markers, example-path existence, the Go analyzer registry (via the
  ``cmd/analyzers-json`` JSON bridge — a dead bridge is a LOUD error, never an
  empty column), the tessercheck-py ``CHECKS`` registry (direct import), and
  rationale-test globs.
- **Judgment cells** are ``tb-cell`` annotations at the source they describe
  (schema: ``docs/skill-authoring.md``); a malformed marker is a named error
  with file:line.
- Any file marked ``tb-status: stub|partial`` must carry the 2A disclaimer
  text (machine-checked, eng review 6A).
- Living markdown surfaces must not reference nonexistent repo paths
  (backticked paths only; suppress an intentional forward reference with
  ``tb-allow-missing:``).

Run ``python3 roadmap/generate.py`` to regenerate in place; ``--check`` (CI)
fails on any drift between the committed rendering and the derivation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SYMBOL_DONE = "✅"  # ✅
SYMBOL_PARTIAL = "\U0001f7e1"  # 🟡
SYMBOL_ABSENT = "❌"  # ❌
SYMBOL_NA = "—"  # —
SYMBOLS = (SYMBOL_DONE, SYMBOL_PARTIAL, SYMBOL_ABSENT, SYMBOL_NA)

COLUMNS = ("py-example", "go-example", "skill", "checker", "rationale")

ROW_KEYS_ALLOWED = {
    "key",
    "title",
    "skill",
    "py_example",
    "go_example",
    "go_analyzers",
    "py_checks",
    "enforcement_tests",
    "rationale",
}

# The 2A stub-contract phrases every stub/partial doc must carry (machine check).
DISCLAIMER_PHRASES = ("not yet materialized", "don't invent a convention")

# Directories scanned for tb-cell / tb-status markers. roadmap/ itself and
# docs/ are excluded on purpose: the schema documentation and the test
# fixtures both quote the grammar without being annotations.
MARKER_SCAN_DIRS = ("skills", "examples", "rationale", "passes", "tessercheck-py")
MARKER_SCAN_EXTS = (".md", ".go", ".py")
SKIP_DIR_NAMES = {"__pycache__", ".git", ".claude", "testdata"}

# Living markdown surfaces for the dead-path check (Wave-2 success criteria):
# backticked repo paths on these surfaces must exist. Historical/provenance
# docs (docs/sessions/, design docs) are exempt (eng review D11a).
LIVING_SURFACES = (
    "README.md",
    "docs/start-here.md",
    "docs/faq.md",
    "skills/tesser-build",
    "examples",
)
PATH_TOKEN_RE = re.compile(
    r"`((?:examples|skills|docs|rationale|tessercheck-py|cmd|internal|passes|gclplugin)"
    r"/[A-Za-z0-9_./-]*)`"
)

CELL_RE = re.compile(
    r"tb-cell:\s*(?P<row>[a-z0-9-]+)\s+(?P<col>[a-z-]+)\s+(?P<symbol>\S+)"
    r"(?:\s+--\s+(?P<text>.*?))?\s*(?:-->)?\s*$"
)
STATUS_RE = re.compile(r"tb-status:\s*(?P<status>[a-z]+)\s*(?:-->)?\s*$")
ALLOW_MISSING_RE = re.compile(r"tb-allow-missing:\s*(?P<path>\S+)\s*(?:-->)?\s*$")


class RoadmapError(Exception):
    """A named derivation error — always carries enough context to act on."""


@dataclass(frozen=True)
class CellAnnotation:
    row: str
    column: str
    symbol: str
    text: str
    location: str  # file:line


@dataclass(frozen=True)
class Markers:
    cells: dict[tuple[str, str], CellAnnotation]
    statuses: dict[str, tuple[str, str]]  # relpath -> (status, location)
    allow_missing: dict[str, set[str]]  # relpath -> suppressed path tokens


def iter_marker_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for top in MARKER_SCAN_DIRS:
        base = root / top
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_dir():
                continue
            if p.suffix not in MARKER_SCAN_EXTS:
                continue
            if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
                continue
            files.append(p)
    return files


def scan_markers(root: Path, row_keys: set[str]) -> Markers:
    cells: dict[tuple[str, str], CellAnnotation] = {}
    statuses: dict[str, tuple[str, str]] = {}
    allow_missing: dict[str, set[str]] = {}
    for path in iter_marker_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            loc = f"{rel}:{lineno}"
            if "tb-cell:" in line:
                m = CELL_RE.search(line)
                if m is None:
                    raise RoadmapError(f"{loc}: malformed tb-cell marker: {line.strip()!r}")
                row, col, symbol = m.group("row"), m.group("col"), m.group("symbol")
                if row not in row_keys:
                    raise RoadmapError(f"{loc}: tb-cell names unknown row {row!r} (registry keys: {sorted(row_keys)})")
                if col not in COLUMNS:
                    raise RoadmapError(f"{loc}: tb-cell names unknown column {col!r} (allowed: {COLUMNS})")
                if symbol not in SYMBOLS:
                    raise RoadmapError(f"{loc}: tb-cell symbol {symbol!r} not in {SYMBOLS}")
                key = (row, col)
                if key in cells:
                    raise RoadmapError(
                        f"{loc}: duplicate tb-cell for ({row}, {col}); first at {cells[key].location}"
                    )
                cells[key] = CellAnnotation(row, col, symbol, m.group("text") or "", loc)
            elif "tb-status:" in line:
                m2 = STATUS_RE.search(line)
                if m2 is None:
                    raise RoadmapError(f"{loc}: malformed tb-status marker: {line.strip()!r}")
                status = m2.group("status")
                if status not in ("full", "partial", "stub"):
                    raise RoadmapError(f"{loc}: tb-status must be full|partial|stub, got {status!r}")
                if rel in statuses:
                    raise RoadmapError(f"{loc}: duplicate tb-status; first at {statuses[rel][1]}")
                statuses[rel] = (status, loc)
            elif "tb-allow-missing:" in line:
                m3 = ALLOW_MISSING_RE.search(line)
                if m3 is None:
                    raise RoadmapError(f"{loc}: malformed tb-allow-missing marker: {line.strip()!r}")
                allow_missing.setdefault(rel, set()).add(m3.group("path"))
        # 6A: a stub/partial doc must carry the 2A disclaimer text.
        if rel in statuses and statuses[rel][0] in ("partial", "stub"):
            # Normalize whitespace (and blockquote markers) so a phrase wrapped
            # across lines still matches.
            unquoted = " ".join(line.lstrip("> ") for line in text.splitlines())
            lowered = " ".join(unquoted.lower().split())
            for phrase in DISCLAIMER_PHRASES:
                if phrase not in lowered:
                    raise RoadmapError(
                        f"{rel}: tb-status {statuses[rel][0]} but the 2A disclaimer phrase "
                        f"{phrase!r} is missing (see docs/skill-authoring.md, stub contract)"
                    )
    return Markers(cells, statuses, allow_missing)


def go_analyzer_names(root: Path, cmd: list[str]) -> set[str]:
    try:
        out = subprocess.run(
            cmd, cwd=root, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise RoadmapError(
            f"Go analyzer bridge failed ({' '.join(cmd)}): {e}. "
            "A dead bridge is a hard failure — the checker column is never silently empty."
        ) from e
    try:
        items = json.loads(out)
    except json.JSONDecodeError as e:
        raise RoadmapError(f"Go analyzer bridge emitted invalid JSON: {e}") from e
    if not isinstance(items, list) or not items:
        raise RoadmapError("Go analyzer bridge returned an empty registry — refusing an empty column")
    names: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            raise RoadmapError(f"Go analyzer bridge item malformed: {item!r}")
        names.add(str(item["name"]))
    return names


def py_check_codes(root: Path) -> set[str]:
    sys.path.insert(0, str(root / "tessercheck-py"))
    try:
        from tessercheck.finding import CHECKS  # noqa: PLC0415 — lazy by design
    except ImportError as e:
        raise RoadmapError(f"cannot import tessercheck-py check registry from {root}: {e}") from e
    finally:
        sys.path.pop(0)
    return {c.code for c in CHECKS}


def load_registry(path: Path) -> list[dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RoadmapError(f"cannot read row registry {path}: {e}") from e
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RoadmapError(f"{path}: registry has no 'rows' list")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise RoadmapError(f"{path}: row is not an object: {row!r}")
        unknown = set(row) - ROW_KEYS_ALLOWED
        if unknown:
            raise RoadmapError(f"{path}: row {row.get('key')!r} has unknown keys {sorted(unknown)}")
        key = row.get("key")
        if not isinstance(key, str) or not key:
            raise RoadmapError(f"{path}: row missing 'key': {row!r}")
        if key in seen:
            raise RoadmapError(f"{path}: duplicate row key {key!r}")
        seen.add(key)
        if not isinstance(row.get("title"), str):
            raise RoadmapError(f"{path}: row {key!r} missing 'title'")
    return [r for r in rows if isinstance(r, dict)]


def _str_list(row: dict[str, object], key: str) -> list[str] | None:
    if key not in row:
        return None
    val = row[key]
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        raise RoadmapError(f"registry row {row.get('key')!r}: {key} must be a list of strings")
    return [str(x) for x in val]


def cell(symbol: str, suffix: str = "") -> str:
    return f"{symbol} {suffix}".strip()


def example_cell(root: Path, paths: list[str] | None) -> str:
    if paths is None:
        return SYMBOL_NA
    if any((root / p).exists() for p in paths):
        return SYMBOL_DONE
    return SYMBOL_ABSENT


def skill_cell(root: Path, row: dict[str, object], markers: Markers) -> str:
    name = row.get("skill")
    if name is None:
        return SYMBOL_NA
    if not isinstance(name, str):
        raise RoadmapError(f"registry row {row.get('key')!r}: skill must be a string")
    rel = f"skills/tesser-build/{name}"
    if not (root / rel).exists():
        return SYMBOL_ABSENT
    if rel not in markers.statuses:
        raise RoadmapError(
            f"{rel}: registry row {row.get('key')!r} names this skill doc but it has no "
            "tb-status marker (add one — see docs/skill-authoring.md, annotation schema)"
        )
    status = markers.statuses[rel][0]
    if status == "full":
        return SYMBOL_DONE
    return cell(SYMBOL_PARTIAL, status)


def checker_cell(
    root: Path,
    row: dict[str, object],
    go_names: set[str] | None,
    py_codes: set[str] | None,
) -> str:
    go_listed = _str_list(row, "go_analyzers")
    py_listed = _str_list(row, "py_checks")
    enforcement = _str_list(row, "enforcement_tests")
    if go_listed is None and py_listed is None and enforcement is None:
        return SYMBOL_NA
    key = row.get("key")
    if go_listed:
        assert go_names is not None
        missing = sorted(set(go_listed) - go_names)
        if missing:
            raise RoadmapError(f"registry row {key!r} lists Go analyzers not in analyzers.All: {missing}")
    if py_listed:
        assert py_codes is not None
        missing = sorted(set(py_listed) - py_codes)
        if missing:
            raise RoadmapError(f"registry row {key!r} lists Python checks not in tessercheck CHECKS: {missing}")
    if go_listed and py_listed:
        return cell(SYMBOL_DONE, f"{len(go_listed)} Go + {len(py_listed)} Py")
    if py_listed:
        return cell(SYMBOL_PARTIAL, f"Py only ({', '.join(py_listed)})")
    if go_listed:
        return cell(SYMBOL_PARTIAL, f"Go only ({', '.join(go_listed)})")
    if enforcement:
        missing_paths = [p for p in enforcement if not (root / p).exists()]
        if missing_paths:
            raise RoadmapError(f"registry row {key!r} enforcement_tests missing on disk: {missing_paths}")
        return cell(SYMBOL_PARTIAL, "in-example")
    return SYMBOL_ABSENT


def rationale_cell(root: Path, row: dict[str, object]) -> str:
    globs = _str_list(row, "rationale")
    if globs is None:
        return SYMBOL_NA
    for pattern in globs:
        if sorted(root.glob(pattern)):
            return SYMBOL_DONE
    return SYMBOL_ABSENT


def dead_path_check(root: Path, markers: Markers) -> list[str]:
    problems: list[str] = []
    surfaces: list[Path] = []
    for entry in LIVING_SURFACES:
        p = root / entry
        if p.is_file():
            surfaces.append(p)
        elif p.is_dir():
            surfaces.extend(sorted(p.rglob("README.md")) if entry == "examples" else sorted(p.glob("*.md")))
    for path in surfaces:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        # Suppressions come from the marker scan AND from the surface itself —
        # living surfaces (e.g. the root README) may sit outside the scan dirs.
        suppressed = set(markers.allow_missing.get(rel, set()))
        for line in text.splitlines():
            if "tb-allow-missing:" in line:
                m0 = ALLOW_MISSING_RE.search(line)
                if m0 is not None:
                    suppressed.add(m0.group("path"))
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in PATH_TOKEN_RE.finditer(line):
                token = m.group(1)
                target = token.split("#", 1)[0].rstrip("/")
                if not target or "*" in target:
                    continue
                if target in suppressed:
                    continue
                if not (root / target).exists():
                    problems.append(
                        f"{rel}:{lineno}: references nonexistent path `{token}` "
                        "(fix it, or mark intentional with tb-allow-missing)"
                    )
    return problems


def render(rows: list[dict[str, object]], cells_by_row: dict[str, dict[str, str]]) -> str:
    lines = [
        "# Roadmap — component × materialization matrix",
        "",
        "<!-- GENERATED by roadmap/generate.py — DO NOT EDIT ANY CELL BY HAND.",
        "     Regenerate: python3 roadmap/generate.py   (CI runs --check).",
        "     Rows come from roadmap/registry.json; judgment cells from tb-cell",
        "     markers at the source they describe (docs/skill-authoring.md). -->",
        "",
        "Legend: ✅ done · 🟡 partial · ❌ absent · — intentionally n/a.",
        "",
        "| Row | Py example | Go example | Skill doc | Checker | Rationale |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        key = str(row["key"])
        c = cells_by_row[key]
        lines.append(
            f"| {row['title']} | {c['py-example']} | {c['go-example']} | "
            f"{c['skill']} | {c['checker']} | {c['rationale']} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate(root: Path, registry_path: Path, analyzers_cmd: list[str]) -> str:
    rows = load_registry(registry_path)
    row_keys = {str(r["key"]) for r in rows}
    markers = scan_markers(root, row_keys)

    need_go = any(_str_list(r, "go_analyzers") for r in rows)
    need_py = any(_str_list(r, "py_checks") for r in rows)
    go_names = go_analyzer_names(root, analyzers_cmd) if need_go else None
    py_codes = py_check_codes(root) if need_py else None

    cells_by_row: dict[str, dict[str, str]] = {}
    for row in rows:
        key = str(row["key"])
        computed = {
            "py-example": example_cell(root, _str_list(row, "py_example")),
            "go-example": example_cell(root, _str_list(row, "go_example")),
            "skill": skill_cell(root, row, markers),
            "checker": checker_cell(root, row, go_names, py_codes),
            "rationale": rationale_cell(root, row),
        }
        for col in COLUMNS:
            ann = markers.cells.get((key, col))
            if ann is not None:
                computed[col] = cell(ann.symbol, ann.text)
        cells_by_row[key] = computed

    problems = dead_path_check(root, markers)
    if problems:
        raise RoadmapError("living surfaces reference nonexistent paths:\n" + "\n".join(problems))

    return render(rows, cells_by_row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--analyzers-cmd",
        default="go run ./cmd/analyzers-json",
        help="command producing the analyzers.All JSON dump (whitespace-split)",
    )
    parser.add_argument("--check", action="store_true", help="fail if the committed rendering drifted")
    args = parser.parse_args(argv)

    root: Path = args.root
    registry = args.registry if args.registry is not None else root / "roadmap" / "registry.json"
    output = args.output if args.output is not None else root / "roadmap" / "ROADMAP.md"

    try:
        content = generate(root, registry, str(args.analyzers_cmd).split())
    except RoadmapError as e:
        print(f"roadmap: {e}", file=sys.stderr)
        return 2

    if args.check:
        if not output.exists():
            print(f"roadmap: {output} does not exist — run python3 roadmap/generate.py", file=sys.stderr)
            return 1
        committed = output.read_text(encoding="utf-8")
        if committed != content:
            print(
                f"roadmap: {output} has drifted from the derivation — "
                "run python3 roadmap/generate.py and commit the result",
                file=sys.stderr,
            )
            return 1
        print("roadmap: up to date")
        return 0

    output.write_text(content, encoding="utf-8")
    print(f"roadmap: wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
