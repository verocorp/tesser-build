from __future__ import annotations

import os
import subprocess
import sys
import pathlib



def test_a_clean_repo_exits_zero_with_the_app_rows(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('manifest.json', '{".github": "ungated", "appone": "app", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
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
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('manifest.json', '{".github": "ungated", "appone": "app", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    tree = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "srv.cli.trees", str(tmp_path), "extra"],
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
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('manifest.json', '{".github": "ungated", "appone": "app", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
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
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('manifest.json', '{".github": "ungated", "appone": "app", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
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
