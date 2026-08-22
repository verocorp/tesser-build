from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import tesser.testing as ts

@ts.helper
def _repo(root: Path) -> Path:  # tesser:debt TB073
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


def test_a_missing_root_argument_exits_two_with_the_usage() -> None:
    tree = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.check"],
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
    assert "usage: python -m srv.cli.check" in result.stderr


def test_an_extra_argument_exits_two() -> None:
    tree = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.check", "/r", "extra"],
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
    assert "usage: python -m srv.cli.check" in result.stderr


def test_a_clean_repo_exits_zero_with_the_summary(tmp_path: Path) -> None:
    tree = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.check", str(_repo(tmp_path))],
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
    assert "3 rows, 1 app trees" in result.stdout
    assert result.stderr == ""


def test_problems_exit_one_on_stderr(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "stray").mkdir()
    tree = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.check", str(tmp_path)],
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
    assert "layout: " in result.stderr
