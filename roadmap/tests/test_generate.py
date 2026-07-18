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
