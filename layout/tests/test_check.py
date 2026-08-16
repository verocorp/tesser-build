from __future__ import annotations

from pathlib import Path

import tesser.testing as ts

import repo.client.client as client
import repo.wiring.config as config
import repo.wiring.wire as wire


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
    (root / "docs").mkdir()
    (root / "examples" / "demo").mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{".github": "ungated", "appone": "app", "docs": "ungated",'
        ' "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'
    )
    return root


def test_a_consistent_repo_checks_clean(tmp_path: Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(root=str(_repo(tmp_path))))
    assert response.problems == ()
    assert response.counts == ("6", "1")


def test_an_unregistered_directory_is_reported_through_the_stack(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in response.problems)


def test_trees_lists_app_rows_through_the_client(tmp_path: Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.trees(client.TreesRequest(root=str(_repo(tmp_path))))
    assert response.trees == ("appone",)


def test_a_malformed_manifest_is_one_message_not_a_crash(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(root=str(tmp_path)))
    assert len(response.problems) == 1
    assert "manifest.json is unreadable" in response.problems[0]


def test_a_nonexistent_root_is_a_problem_not_a_crash(tmp_path: Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.check(
        client.CheckRequest(root=str(tmp_path / "no-such-dir"))
    )
    assert len(response.problems) == 1
    assert "is not a directory" in response.problems[0]
