"""The 6A test suite for the roadmap generator (eng review 6A):

- golden output: the committed ROADMAP.md equals the live derivation (this is
  also CI's drift teeth-test — any input mutation changes the derivation and
  fails the comparison);
- an explicit teeth-test on a fixture tree: mutate an input → the output cell
  flips;
- the Go JSON bridge dying is a loud failure, never an empty column;
- a malformed annotation is a named error carrying file:line;
- a file annotated ``tb-status: stub`` must contain the 2A disclaimer text;
- the dead-path check flags a nonexistent backticked path on a living surface
  and honors ``tb-allow-missing``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "roadmap_generate", REPO_ROOT / "roadmap" / "generate.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["roadmap_generate"] = mod
    spec.loader.exec_module(mod)
    return mod


gen = _load_generator()

# The verified-impl path is deliberately NOT backticked so the teeth-test can
# delete the path without also tripping the dead-path check on this doc.
STUB_DOC = (
    "# Widget\n\n<!-- tb-status: stub -->\n\n"
    "Not yet materialized; note the gap, don't invent a convention; the "
    "verified impl is examples/fixture-app/widget.\n"
)


def make_fixture(tmp_path: Path, *, skill_doc: str = STUB_DOC) -> tuple[Path, Path]:
    """A minimal repo tree with one registry row and one skill doc."""
    root = tmp_path / "repo"
    skills = root / "skills" / "tesser-build"
    skills.mkdir(parents=True)
    (skills / "widget.md").write_text(skill_doc, encoding="utf-8")
    (root / "examples" / "fixture-app" / "widget").mkdir(parents=True)
    registry = root / "roadmap"
    registry.mkdir()
    (registry / "registry.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "key": "widget",
                        "title": "Widget",
                        "skill": "widget.md",
                        "py_example": ["examples/fixture-app/widget"],
                        "rationale": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return root, registry / "registry.json"


def generate_fixture(root: Path, registry: Path) -> str:
    # No row lists go_analyzers/py_checks, so neither bridge is invoked; a
    # deliberately-broken cmd proves that.
    out = gen.generate(root, registry, ["false"])
    assert isinstance(out, str)
    return out


def test_golden_committed_roadmap_matches_derivation() -> None:
    """The committed rendering equals the live derivation (drift teeth-test:
    mutating any generator input — a skill file, the registry, an annotation,
    a checker registry — changes the derivation and fails this)."""
    committed = (REPO_ROOT / "roadmap" / "ROADMAP.md").read_text(encoding="utf-8")
    derived = gen.generate(
        REPO_ROOT,
        REPO_ROOT / "roadmap" / "registry.json",
        "go run ./cmd/analyzers-json".split(),
    )
    assert isinstance(derived, str)
    assert committed == derived, "roadmap/ROADMAP.md drifted — run python3 roadmap/generate.py"


def test_teeth_deleting_an_input_flips_the_cell(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    before = generate_fixture(root, registry)
    assert "| Widget | ✅ |" in before

    (root / "examples" / "fixture-app" / "widget").rmdir()
    after = generate_fixture(root, registry)
    assert "| Widget | ❌ |" in after
    assert before != after


def test_dead_bridge_is_loud(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["rows"][0]["go_analyzers"] = ["mustnew"]
    registry.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match="bridge failed"):
        gen.generate(root, registry, ["false"])


def test_malformed_annotation_names_file_and_line(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    bad = root / "examples" / "fixture-app" / "widget" / "note.md"
    bad.write_text("line one\n<!-- tb-cell: widget nonsense -->\n", encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match=r"note\.md:2"):
        generate_fixture(root, registry)


def test_unknown_row_in_annotation_is_an_error(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    bad = root / "examples" / "fixture-app" / "widget" / "note.md"
    bad.write_text("<!-- tb-cell: nosuchrow py-example ✅ -->\n", encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match="unknown row"):
        generate_fixture(root, registry)


def test_duplicate_cell_annotation_is_an_error(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    a = root / "examples" / "fixture-app" / "widget" / "a.md"
    b = root / "examples" / "fixture-app" / "widget" / "b.md"
    a.write_text("<!-- tb-cell: widget py-example 🟡 -- one -->\n", encoding="utf-8")
    b.write_text("<!-- tb-cell: widget py-example ✅ -- two -->\n", encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match="duplicate tb-cell"):
        generate_fixture(root, registry)


def test_annotation_overrides_mechanical_cell(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    note = root / "examples" / "fixture-app" / "widget" / "note.md"
    note.write_text("<!-- tb-cell: widget py-example 🟡 -- half done -->\n", encoding="utf-8")
    out = generate_fixture(root, registry)
    assert "| Widget | 🟡 half done |" in out


def test_stub_without_disclaimer_is_an_error(tmp_path: Path) -> None:
    root, registry = make_fixture(
        tmp_path, skill_doc="# Widget\n\n<!-- tb-status: stub -->\n\nNothing here.\n"
    )
    with pytest.raises(gen.RoadmapError, match="2A disclaimer"):
        generate_fixture(root, registry)


def test_missing_status_marker_is_an_error(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path, skill_doc="# Widget\n\nNo marker at all.\n")
    with pytest.raises(gen.RoadmapError, match="tb-status"):
        generate_fixture(root, registry)


def _add_rule_row(registry: Path, **overrides: object) -> None:
    data = json.loads(registry.read_text(encoding="utf-8"))
    row: dict[str, object] = {
        "key": "rule-direction",
        "title": "Dependency direction",
        "kind": "rule",
        "taught_in": "skills/tesser-build/widget.md",
        "enforced_by": "import-linter",
    }
    row.update(overrides)
    data["rows"].append(row)
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_rule_row_renders_in_second_table(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry)
    out = generate_fixture(root, registry)
    assert "## Pay-now rules" in out
    assert "| Rule | Taught in | Enforced by | Status |" in out
    assert (
        "| Dependency direction | `skills/tesser-build/widget.md` | "
        "import-linter | ✅ taught + enforcer declared |" in out
    )
    # The rule row must NOT leak into the component table.
    component_table = out.split("## Pay-now rules")[0]
    assert "Dependency direction" not in component_table


def test_no_rule_rows_means_no_second_table(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    assert "## Pay-now rules" not in generate_fixture(root, registry)


def test_malformed_kind_is_a_named_file_line_error(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, kind="rulez")
    with pytest.raises(gen.RoadmapError, match=r"registry\.json:\d+.*malformed kind 'rulez'"):
        generate_fixture(root, registry)


def test_rule_row_rejects_component_keys(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, py_example=["examples/fixture-app/widget"])
    with pytest.raises(gen.RoadmapError, match="unknown keys.*py_example"):
        generate_fixture(root, registry)


def test_teeth_deleting_taught_in_target_flips_rule_status(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry)
    assert "✅ taught + enforcer declared" in generate_fixture(root, registry)

    (root / "skills" / "tesser-build" / "widget.md").unlink()
    after = generate_fixture(root, registry)
    assert "🟡 enforcer declared only" in after
    assert "❌ `skills/tesser-build/widget.md`" in after


def test_rule_row_with_neither_field_is_bare_absent(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["rows"].append({"key": "rule-bare", "title": "Bare rule", "kind": "rule"})
    registry.write_text(json.dumps(data), encoding="utf-8")
    out = generate_fixture(root, registry)
    assert "| Bare rule | ❌ | ❌ | ❌ |" in out


def test_empty_taught_in_is_a_named_error(tmp_path: Path) -> None:
    """'' used to resolve to the repo root (always exists) and silently
    render as taught (cumulative review, testing specialist)."""
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, taught_in="")
    with pytest.raises(gen.RoadmapError, match="taught_in must be a non-empty"):
        generate_fixture(root, registry)


def test_pipe_in_rule_field_is_a_named_error(tmp_path: Path) -> None:
    """A '|' in a cell-bound field fabricates table columns and the drift
    check can't see it (cumulative review F7)."""
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, enforced_by="import-linter | totally fine")
    with pytest.raises(gen.RoadmapError, match="must not contain"):
        generate_fixture(root, registry)


def test_bad_anchor_in_taught_in_is_a_named_error(tmp_path: Path) -> None:
    """taught_in#anchor must resolve to an explicit {#anchor} heading id in
    the target (cumulative review F8: bad anchors rendered green)."""
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, taught_in="skills/tesser-build/widget.md#nonexistent-anchor")
    with pytest.raises(gen.RoadmapError, match="anchor #nonexistent-anchor not found"):
        generate_fixture(root, registry)


def test_empty_anchor_fragment_is_a_named_error(tmp_path: Path) -> None:
    """'path#' used to skip anchor validation entirely (Codex P2)."""
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry, taught_in="skills/tesser-build/widget.md#")
    with pytest.raises(gen.RoadmapError, match="empty #fragment"):
        generate_fixture(root, registry)


def test_anchor_in_body_text_does_not_count(tmp_path: Path) -> None:
    """The anchor must sit on a heading line — a body-text mention of the
    {#id} token is not a heading id (Codex P2)."""
    root, registry = make_fixture(tmp_path)
    doc = root / "skills" / "tesser-build" / "widget.md"
    doc.write_text(
        doc.read_text(encoding="utf-8") + "\nThe id {#rules} is discussed here.\n",
        encoding="utf-8",
    )
    _add_rule_row(registry, taught_in="skills/tesser-build/widget.md#rules")
    with pytest.raises(gen.RoadmapError, match="anchor #rules not found"):
        generate_fixture(root, registry)


def test_good_anchor_in_taught_in_renders_taught(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    doc = root / "skills" / "tesser-build" / "widget.md"
    doc.write_text(doc.read_text(encoding="utf-8") + "\n## Rules {#rules}\n", encoding="utf-8")
    _add_rule_row(registry, taught_in="skills/tesser-build/widget.md#rules")
    assert "✅ taught + enforcer declared" in generate_fixture(root, registry)


def test_row_location_tolerates_compact_json(tmp_path: Path) -> None:
    """The file:line lookup must survive non-default JSON spacing
    (cumulative review F10: the needle assumed '\"key\": \"...\"')."""
    root, registry = make_fixture(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["rows"].append(
        {"key": "rule-compact", "title": "Compact", "kind": "rulez"}
    )
    registry.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match=r"registry\.json:\d+.*malformed kind"):
        generate_fixture(root, registry)


def test_rule_row_without_enforcer_is_taught_only(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["rows"].append(
        {
            "key": "rule-direction",
            "title": "Dependency direction",
            "kind": "rule",
            "taught_in": "skills/tesser-build/widget.md",
        }
    )
    registry.write_text(json.dumps(data), encoding="utf-8")
    assert "🟡 taught only" in generate_fixture(root, registry)


def test_tb_cell_naming_a_rule_row_is_unknown_row(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    _add_rule_row(registry)
    note = root / "examples" / "fixture-app" / "widget" / "note.md"
    note.write_text("<!-- tb-cell: rule-direction checker ✅ -->\n", encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match="unknown row"):
        generate_fixture(root, registry)


def test_dead_path_check_flags_and_allows(tmp_path: Path) -> None:
    root, registry = make_fixture(tmp_path)
    readme = root / "README.md"
    readme.write_text("See `examples/nope` for details.\n", encoding="utf-8")
    with pytest.raises(gen.RoadmapError, match="nonexistent path"):
        generate_fixture(root, registry)

    readme.write_text(
        "<!-- tb-allow-missing: examples/nope -->\nSee `examples/nope` for details.\n",
        encoding="utf-8",
    )
    # tb-allow-missing markers on the surface itself are honored — but README.md
    # is outside the marker-scan dirs, so the suppression must be scanned from
    # living surfaces too; this asserts it is.
    out = generate_fixture(root, registry)
    assert "Widget" in out
