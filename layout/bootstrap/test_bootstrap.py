from __future__ import annotations

from pathlib import Path

import tesser.testing as ts

from bootstrap.bootstrap import new
import repo.client.client as client


@ts.helper
def _repo(root: Path) -> Path:  # tessercheck:ignore TB073
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


def test_the_app_checks_a_clean_repo_through_its_repo_client(tmp_path: Path) -> None:
    response = new().repo.check(client.CheckRequest(root=str(_repo(tmp_path))))
    assert response.problems == ()
    assert response.counts == ("3", "1")


def test_the_app_reports_an_unregistered_directory(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    response = new().repo.check(client.CheckRequest(root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in response.problems)


def test_the_app_lists_the_app_trees(tmp_path: Path) -> None:
    response = new().repo.trees(client.TreesRequest(root=str(_repo(tmp_path))))
    assert response.trees == ("appone",)


def test_a_nonexistent_root_is_a_problem_not_a_crash(tmp_path: Path) -> None:
    response = new().repo.check(
        client.CheckRequest(root=str(tmp_path / "no-such-dir"))
    )
    assert len(response.problems) == 1
    assert "is not a directory" in response.problems[0]


def test_a_broken_manifest_is_one_message_not_a_crash(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = new().repo.check(client.CheckRequest(root=str(tmp_path)))
    assert len(response.problems) == 1
    assert "manifest.json is unreadable" in response.problems[0]


def test_each_app_gets_its_own_repo_client(tmp_path: Path) -> None:
    first = new()
    second = new()
    assert first.repo is not second.repo
    assert first.repo.check(
        client.CheckRequest(root=str(_repo(tmp_path)))
    ).problems == ()
    assert second.repo.check(client.CheckRequest(root=str(tmp_path))).problems == ()
