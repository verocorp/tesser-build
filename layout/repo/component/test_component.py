from __future__ import annotations

import pathlib

import tesser.testing as ts

import repo.client.client as client
import repo.component.config as config
import repo.component.component as wire


@ts.helper
def _repo(root: pathlib.Path) -> pathlib.Path:  # tesser:debt TB073
    (root / "scripts").mkdir()
    (root / "scripts" / "verify").write_text(
        "run_appone() {\n"
        "  tessercheck_tree . || return 1\n"
        "}\n"
        "run_tree() {\n"
        '  case "$1" in\n'
        '    appone)   run_appone ;;\n'
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


def test_the_built_client_checks_a_clean_repo_off_disk(tmp_path: pathlib.Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(repo_root=str(_repo(tmp_path))))
    assert response.problems == ()
    assert response.counts == ("3", "1")


def test_the_built_client_reads_the_filesystem_it_is_pointed_at(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(repo_root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in response.problems)


def test_the_built_client_lists_the_app_trees(tmp_path: pathlib.Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.trees(client.TreesRequest(repo_root=str(_repo(tmp_path))))
    assert response.trees == ("appone",)


def test_the_built_client_turns_a_missing_root_into_a_problem(tmp_path: pathlib.Path) -> None:
    response = wire.Repo(config.Config(config.Spec())).client.check(
        client.CheckRequest(repo_root=str(tmp_path / "no-such-dir"))
    )
    assert len(response.problems) == 1
    assert "is not a directory" in response.problems[0]


def test_the_built_client_turns_a_broken_manifest_into_one_problem(
    tmp_path: pathlib.Path,
) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = wire.Repo(config.Config(config.Spec())).client.check(client.CheckRequest(repo_root=str(tmp_path)))
    assert len(response.problems) == 1
    assert "manifest.json is unreadable" in response.problems[0]


def test_every_build_hands_back_a_separate_client(tmp_path: pathlib.Path) -> None:
    first = wire.Repo(config.Config(config.Spec())).client
    second = wire.Repo(config.Config(config.Spec())).client
    assert first is not second
    assert first.check(
        client.CheckRequest(repo_root=str(_repo(tmp_path)))
    ).problems == ()
    assert second.check(client.CheckRequest(repo_root=str(tmp_path))).problems == ()
