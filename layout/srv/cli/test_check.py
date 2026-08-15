from __future__ import annotations

from pathlib import Path

import tesser.testing as ts

from bootstrap.bootstrap import new
import repo.adapters.handlers.cli as cli
from srv.cli.check import respond as check_respond
from srv.cli.trees import respond as trees_respond


@ts.helper
def _repo(root: Path) -> Path:  # tessercheck:ignore TB073
    (root / "scripts").mkdir()
    (root / "scripts" / "verify").write_text(
        "run_appone() {\n"
        "  PYTHONPATH=x python3 -m tessercheck . || return 1\n"
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


def test_a_missing_root_argument_exits_two() -> None:
    response = check_respond(cli.Handler(new().repo), [])
    assert response.exit_code == 2
    assert "usage:" in response.stderr


def test_an_extra_argument_exits_two() -> None:
    response = check_respond(cli.Handler(new().repo), ["/r", "extra"])
    assert response.exit_code == 2


def test_a_clean_repo_exits_zero_with_the_summary(tmp_path: Path) -> None:
    response = check_respond(cli.Handler(new().repo), [str(_repo(tmp_path))])
    assert response.exit_code == 0
    assert "3 rows, 1 app trees" in response.stdout


def test_problems_exit_one_on_stderr(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "stray").mkdir()
    response = check_respond(cli.Handler(new().repo), [str(tmp_path)])
    assert response.exit_code == 1
    assert "layout: " in response.stderr


def test_trees_prints_app_rows(tmp_path: Path) -> None:
    response = trees_respond(cli.Handler(new().repo), [str(_repo(tmp_path))])
    assert response.exit_code == 0
    assert response.stdout == "appone"


def test_trees_with_no_argument_exits_two() -> None:
    response = trees_respond(cli.Handler(new().repo), [])
    assert response.exit_code == 2


def test_trees_on_a_broken_manifest_exits_one(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = trees_respond(cli.Handler(new().repo), [str(tmp_path)])
    assert response.exit_code == 1
    assert "manifest.json is unreadable" in response.stderr
