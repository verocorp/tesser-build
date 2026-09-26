from __future__ import annotations

import pathlib

import repo.client as client
import repo.component as component


def test_a_config_constructs_from_its_spec() -> None:
    assert isinstance(component.Config(component.Spec()), component.Config)


def test_each_config_is_its_own() -> None:
    assert component.Config(component.Spec()) is not component.Config(component.Spec())


def test_the_built_client_checks_a_clean_repo_off_disk(tmp_path: pathlib.Path) -> None:
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
    check_layout_response = component.Repo(component.Config(component.Spec())).client.check_layout(client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert check_layout_response.problems == ()
    assert check_layout_response.counts == ("3", "1")


def test_the_built_client_reads_the_filesystem_it_is_pointed_at(tmp_path: pathlib.Path) -> None:
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
    check_layout_response = component.Repo(component.Config(component.Spec())).client.check_layout(client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in check_layout_response.problems)


def test_the_built_client_lists_the_app_trees(tmp_path: pathlib.Path) -> None:
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
    list_trees_response = component.Repo(component.Config(component.Spec())).client.list_trees(client.ListTreesRequest(repo_root=str(tmp_path)))
    assert list_trees_response.trees == ("appone",)


def test_the_built_client_turns_a_missing_root_into_a_problem(tmp_path: pathlib.Path) -> None:
    check_layout_response = component.Repo(component.Config(component.Spec())).client.check_layout(
        client.CheckLayoutRequest(repo_root=str(tmp_path / "no-such-dir"))
    )
    assert len(check_layout_response.problems) == 1
    assert "is not a directory" in check_layout_response.problems[0]


def test_the_built_client_turns_a_broken_manifest_into_one_problem(
    tmp_path: pathlib.Path,
) -> None:
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
    check_layout_response = component.Repo(component.Config(component.Spec())).client.check_layout(client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert len(check_layout_response.problems) == 1
    assert "manifest.json is unreadable" in check_layout_response.problems[0]


def test_every_build_hands_back_a_separate_client(tmp_path: pathlib.Path) -> None:
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
    first = component.Repo(component.Config(component.Spec())).client
    second = component.Repo(component.Config(component.Spec())).client
    assert first is not second
    assert first.check_layout(
        client.CheckLayoutRequest(repo_root=str(tmp_path))
    ).problems == ()
    assert second.check_layout(client.CheckLayoutRequest(repo_root=str(tmp_path))).problems == ()
