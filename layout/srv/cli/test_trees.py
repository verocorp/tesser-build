from __future__ import annotations

import os
import subprocess
import sys
import pathlib

import tesser.testing as ts

@ts.helper
def _repo(root: pathlib.Path) -> pathlib.Path:  # tesser:debt TB073
    (root / "scripts").mkdir()
    (root / "scripts" / "verify").write_text(
        "run_appone() {\n"
        "  tessercheck_tree . || return 1\n"
        "}\n"
        "run_tree() {\n"
        '  case "$1" in\n'
        "    appone)   run_appone ;;\n"
        "  esac\n"
        "}\n"
    )
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "test.yml").write_text(
        "jobs:\n"
        "  appone:\n"
        "    steps:\n"
        "      - name: gate\n"
        "        run: scripts/verify appone\n"
    )
    (root / "appone").mkdir()
    (root / "appone" / ".tesser-root").write_text("app\n")
    (root / "appone" / "requirements-dev.txt").write_text("pytest\n")
    (root / "manifest.json").write_text(
        '{".github": "ungated", "appone": "app", "scripts": "ungated"}'
    )
    return root


def test_a_clean_repo_exits_zero_with_the_app_rows(tmp_path: pathlib.Path) -> None:
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees", str(_repo(tmp_path))],
        cwd=tree,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(tree), str(tree.parent / "tesser-py")]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == "appone\n"
    assert result.stderr == ""


def test_a_missing_root_argument_exits_two_with_the_usage() -> None:
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees"],
        cwd=tree,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(tree), str(tree.parent / "tesser-py")]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage: python -m srv.cli.trees" in result.stderr


def test_an_extra_argument_exits_two_with_the_usage(tmp_path: pathlib.Path) -> None:
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees", str(_repo(tmp_path)), "extra"],
        cwd=tree,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(tree), str(tree.parent / "tesser-py")]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "usage: python -m srv.cli.trees" in result.stderr


def test_a_broken_manifest_exits_one_on_stderr(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees", str(tmp_path)],
        cwd=tree,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(tree), str(tree.parent / "tesser-py")]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "manifest.json is unreadable" in result.stderr


def test_an_unregistered_directory_exits_one_before_listing(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees", str(tmp_path)],
        cwd=tree,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(tree), str(tree.parent / "tesser-py")]
            ),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "no manifest.json row" in result.stderr
