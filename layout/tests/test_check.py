from __future__ import annotations

import pathlib

import repo.client as repo_client
import repo.component as repo_component


def test_a_consistent_repo_checks_clean(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('appone/pyproject.toml', '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'),
        ('docs', None),
        ('examples/demo', None),
        ('manifest.json', '{".github": "ungated", "appone": "app", "docs": "ungated", "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    check_layout_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.check_layout(repo_client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert check_layout_response.problems == ()
    assert check_layout_response.counts == ("6", "1")


def test_an_unregistered_directory_is_reported_through_the_stack(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('appone/pyproject.toml', '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'),
        ('docs', None),
        ('examples/demo', None),
        ('manifest.json', '{".github": "ungated", "appone": "app", "docs": "ungated", "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    (tmp_path / "utils").mkdir()
    check_layout_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.check_layout(repo_client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in check_layout_response.problems)


def test_trees_lists_app_rows_through_the_client(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('appone/pyproject.toml', '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'),
        ('docs', None),
        ('examples/demo', None),
        ('manifest.json', '{".github": "ungated", "appone": "app", "docs": "ungated", "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    list_trees_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.list_trees(repo_client.ListTreesRequest(repo_root=str(tmp_path)))
    assert list_trees_response.trees == ("appone",)


def test_a_malformed_manifest_is_one_message_not_a_crash(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('appone/pyproject.toml', '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'),
        ('docs', None),
        ('examples/demo', None),
        ('manifest.json', '{".github": "ungated", "appone": "app", "docs": "ungated", "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    (tmp_path / "manifest.json").write_text("{ truncated")
    check_layout_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.check_layout(repo_client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert len(check_layout_response.problems) == 1
    assert "manifest.json is unreadable" in check_layout_response.problems[0]


def test_a_nonexistent_root_is_a_problem_not_a_crash(tmp_path: pathlib.Path) -> None:
    check_layout_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.check_layout(
        repo_client.CheckLayoutRequest(repo_root=str(tmp_path / "no-such-dir"))
    )
    assert len(check_layout_response.problems) == 1
    assert "is not a directory" in check_layout_response.problems[0]


def test_a_stale_python_floor_is_reported_through_the_stack(tmp_path: pathlib.Path) -> None:
    repo_files: tuple[tuple[str, str | None], ...] = (
        ('scripts', None),
        ('scripts/verify', 'run_appone() {\n  tessercheck_tree . || return 1\n}\nrun_tree() {\n  case "$1" in\n    appone)   run_appone ;;\n  esac\n}\n'),
        ('.github/workflows', None),
        ('.github/workflows/test.yml', 'jobs:\n  appone:\n    steps:\n      - name: gate\n        run: scripts/verify appone\n'),
        ('appone', None),
        ('appone/.tesser-root', 'app\n'),
        ('appone/requirements-dev.txt', 'pytest\n'),
        ('appone/pyproject.toml', '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'),
        ('docs', None),
        ('examples/demo', None),
        ('manifest.json', '{".github": "ungated", "appone": "app", "docs": "ungated", "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'),
    )
    for name, text in repo_files:
        path = tmp_path / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.write_text(text)
    (tmp_path / "appone" / "pyproject.toml").write_text(
        '[project]\nname = "appone"\nrequires-python = ">=3.11"\n'
    )
    check_layout_response = repo_component.Repo(repo_component.Config(repo_component.Spec())).client.check_layout(repo_client.CheckLayoutRequest(repo_root=str(tmp_path)))
    assert any("the Python floor is 3.12" in p for p in check_layout_response.problems), check_layout_response.problems
