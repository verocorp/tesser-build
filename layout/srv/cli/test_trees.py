from __future__ import annotations

from pathlib import Path

import pytest
import tesser.testing as ts

from app.loader import load
import repo.adapters.handlers.cli as cli
from srv.cli.trees import respond, run


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


def test_a_clean_repo_exits_zero_with_the_app_rows(tmp_path: Path) -> None:
    response = respond(cli.Handler(load().repo.client), [str(_repo(tmp_path))])
    assert response.exit_code == 0
    assert response.stdout == "appone"
    assert response.stderr == ""


def test_a_missing_root_argument_exits_two_with_the_usage() -> None:
    response = respond(cli.Handler(load().repo.client), [])
    assert response.exit_code == 2
    assert response.stdout == ""
    assert "usage: python -m srv.cli.trees" in response.stderr


def test_an_extra_argument_exits_two_with_the_usage(tmp_path: Path) -> None:
    response = respond(cli.Handler(load().repo.client), [str(_repo(tmp_path)), "extra"])
    assert response.exit_code == 2
    assert "usage: python -m srv.cli.trees" in response.stderr


def test_a_broken_manifest_exits_one_on_stderr(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = respond(cli.Handler(load().repo.client), [str(tmp_path)])
    assert response.exit_code == 1
    assert response.stdout == ""
    assert "manifest.json is unreadable" in response.stderr


def test_an_unregistered_directory_exits_one_before_listing(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    response = respond(cli.Handler(load().repo.client), [str(tmp_path)])
    assert response.exit_code == 1
    assert "no manifest.json row" in response.stderr


def test_run_prints_the_trees_to_stdout_and_returns_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run([str(_repo(tmp_path))])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "appone\n"
    assert captured.err == ""


def test_run_prints_a_usage_error_to_stderr_and_returns_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = run([])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "usage: python -m srv.cli.trees" in captured.err


def test_run_prints_problems_to_stderr_and_returns_one(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    assert run([str(tmp_path)]) == 1
