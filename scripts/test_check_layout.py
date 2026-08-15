import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parent / "check-layout"

VERIFY = """#!/usr/bin/env bash
run_appone() {
  tessercheck_tree "$PWD" || return 1
}
run_libby() {
  mypy || return 1
}
run_tree() {
  case "$1" in
    appone)   run_appone ;;
    libby)    run_libby ;;
  esac
}
"""

WORKFLOW = """jobs:
  appone:
    steps:
      - name: gate
        run: scripts/verify appone
  libby:
    steps:
      - name: gate
        run: scripts/verify libby
"""


def build(root: pathlib.Path) -> None:
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "verify").write_text(VERIFY)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "test.yml").write_text(WORKFLOW)
    (root / "appone").mkdir()
    (root / "appone" / ".tesser-root").write_text("app\n")
    (root / "appone" / "requirements-dev.txt").write_text("pytest\n")
    (root / "libby").mkdir()
    (root / "libby" / "requirements-dev.txt").write_text("mypy\n")
    (root / "docs").mkdir()
    (root / "examples").mkdir()
    (root / "examples" / "demo").mkdir()
    manifest = {
        ".github": "ungated",
        "appone": "app",
        "docs": "ungated",
        "examples": "ungated",
        "examples/demo": "ungated",
        "libby": "app",
        "scripts": "ungated",
    }
    (root / "manifest.json").write_text(json.dumps(manifest))


def rewrite(root: pathlib.Path, changes: dict[str, str]) -> None:
    manifest = json.loads((root / "manifest.json").read_text())
    for key, kind in changes.items():
        if kind == "":
            manifest.pop(key, None)
        else:
            manifest[key] = kind
    (root / "manifest.json").write_text(json.dumps(manifest))


def run(root: pathlib.Path) -> tuple[int, str]:
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True
    )
    return done.returncode, done.stderr + done.stdout


def test_a_consistent_repo_passes(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    code, out = run(tmp_path)
    assert code == 0, out
    assert "agree" in out


def test_an_unknown_kind_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    rewrite(tmp_path, {"libby": "python-library"})
    code, out = run(tmp_path)
    assert code == 1
    assert "unknown kind 'python-library'" in out


def test_a_top_level_dir_without_a_row_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "utils").mkdir()
    code, out = run(tmp_path)
    assert code == 1
    assert "'utils' has no manifest.json row" in out


def test_a_row_without_a_dir_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    rewrite(tmp_path, {"ghost": "ungated"})
    code, out = run(tmp_path)
    assert code == 1
    assert "'ghost' names no directory on disk" in out


def test_an_examples_dir_without_a_row_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "examples" / "newthing").mkdir()
    code, out = run(tmp_path)
    assert code == 1
    assert "examples/newthing has no manifest.json row" in out


def test_a_symlinked_top_level_dir_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (tmp_path / "vendored").symlink_to(outside)
    rewrite(tmp_path, {"vendored": "ungated"})
    code, out = run(tmp_path)
    assert code == 1
    assert "vendored is a symlinked directory" in out


def test_an_app_row_without_a_verify_arm_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "newapp").mkdir()
    (tmp_path / "newapp" / "requirements-dev.txt").write_text("pytest\n")
    rewrite(tmp_path, {"newapp": "app"})
    code, out = run(tmp_path)
    assert code == 1
    assert "no scripts/verify case arm for 'newapp'" in out


def test_an_app_row_without_a_ci_job_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    workflow = (tmp_path / ".github" / "workflows" / "test.yml")
    workflow.write_text(workflow.read_text().replace("run: scripts/verify libby", "run: echo skipped"))
    code, out = run(tmp_path)
    assert code == 1
    assert "no CI job step 'run: scripts/verify libby'" in out


def test_a_commented_ci_job_does_not_count(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    workflow = (tmp_path / ".github" / "workflows" / "test.yml")
    workflow.write_text(workflow.read_text().replace("run: scripts/verify libby", "# run: scripts/verify libby"))
    code, out = run(tmp_path)
    assert code == 1
    assert "no CI job step 'run: scripts/verify libby'" in out


def test_a_tessercheck_arm_without_a_declaration_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "appone" / ".tesser-root").unlink()
    code, out = run(tmp_path)
    assert code == 1
    assert "is missing; a tessercheck-gated tree declares itself" in out


def test_a_declaration_without_a_tessercheck_arm_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "libby" / ".tesser-root").write_text("app\n")
    code, out = run(tmp_path)
    assert code == 1
    assert "declares a tree whose scripts/verify arm does not run tessercheck" in out


def test_a_wrong_declaration_first_line_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_text("domain\n")
    code, out = run(tmp_path)
    assert code == 1
    assert "does not declare 'app': first line is not 'app'" in out


def test_a_declaration_that_is_a_directory_fails_with_a_message(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "appone" / ".tesser-root").unlink()
    (tmp_path / "appone" / ".tesser-root").mkdir()
    code, out = run(tmp_path)
    assert code == 1
    assert "layout:" in out
    assert "Traceback" not in out


def test_a_requirements_dev_outside_an_app_row_fails(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "docs" / "requirements-dev.txt").write_text("sphinx\n")
    code, out = run(tmp_path)
    assert code == 1
    assert "docs holds a requirements-dev.txt but is not an app row" in out


def test_a_nested_python_tree_is_caught_by_the_requirements_check(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    deep = tmp_path / "docs" / "buried" / "tree"
    deep.mkdir(parents=True)
    (deep / "requirements-dev.txt").write_text("pytest\n")
    code, out = run(tmp_path)
    assert code == 1
    assert "docs/buried/tree holds a requirements-dev.txt" in out


def test_a_demoted_app_row_is_caught_by_the_requirements_check(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    rewrite(tmp_path, {"libby": "ungated"})
    code, out = run(tmp_path)
    assert code == 1
    assert "libby holds a requirements-dev.txt but is not an app row" in out


def test_a_skip_dir_is_not_walked(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "appone" / ".venv").mkdir()
    (tmp_path / "appone" / ".venv" / ".tesser-root").write_text("app\n")
    (tmp_path / "appone" / ".venv" / "requirements-dev.txt").write_text("x\n")
    code, out = run(tmp_path)
    assert code == 0, out


def test_a_malformed_manifest_fails_with_a_message(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    code, out = run(tmp_path)
    assert code == 1
    assert "manifest.json is unreadable" in out
    assert "Traceback" not in out


def test_a_wrong_shape_manifest_fails_with_a_message(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "manifest.json").write_text('["a", "b"]')
    code, out = run(tmp_path)
    assert code == 1
    assert "not a flat object" in out
    assert "Traceback" not in out


def test_shared_basenames_across_app_rows_fail(tmp_path: pathlib.Path) -> None:
    build(tmp_path)
    (tmp_path / "examples" / "libby").mkdir()
    (tmp_path / "examples" / "libby" / "requirements-dev.txt").write_text("mypy\n")
    rewrite(tmp_path, {"examples/libby": "app"})
    code, out = run(tmp_path)
    assert code == 1
    assert "share the gate name 'libby'" in out
