from __future__ import annotations

from pathlib import Path

import tesser.testing as ts

import repo.client.client as client
import repo.wiring.wire as wire


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
    (root / "docs").mkdir()
    (root / "examples" / "demo").mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{".github": "ungated", "appone": "app", "docs": "ungated",'
        ' "examples": "ungated", "examples/demo": "ungated", "scripts": "ungated"}'
    )
    return root


def test_a_consistent_repo_checks_clean(tmp_path: Path) -> None:
    response = wire.build().check(client.CheckRequest(root=str(_repo(tmp_path))))
    assert response.problems == ()
    assert response.counts == ("6", "1")


def test_an_unregistered_directory_is_reported(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "utils").mkdir()
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert any("'utils' has no manifest.json row" in p for p in response.problems)


def test_a_symlinked_directory_is_reported(tmp_path: Path) -> None:
    _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (tmp_path / "vendored").symlink_to(outside)
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert any("vendored is a symlinked directory" in p for p in response.problems)


def test_a_deep_requirements_file_is_reported(tmp_path: Path) -> None:
    _repo(tmp_path)
    deep = tmp_path / "docs" / "buried"
    deep.mkdir()
    (deep / "requirements-dev.txt").write_text("pytest\n")
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert any("docs/buried holds a requirements-dev.txt" in p for p in response.problems)


def test_a_bom_prefixed_declaration_still_reads(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert response.problems == ()


def test_a_declaration_under_a_skip_dir_is_not_walked(tmp_path: Path) -> None:
    _repo(tmp_path)
    hidden = tmp_path / "appone" / ".venv"
    hidden.mkdir()
    (hidden / ".tesser-root").write_text("app\n")
    (hidden / "requirements-dev.txt").write_text("x\n")
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert response.problems == ()


def test_a_malformed_manifest_is_a_message_not_a_crash(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert len(response.problems) == 1
    assert "manifest.json is unreadable" in response.problems[0]


def test_trees_lists_app_rows(tmp_path: Path) -> None:
    response = wire.build().trees(client.TreesRequest(root=str(_repo(tmp_path))))
    assert response.trees == ("appone",)


def test_a_dangling_symlink_is_still_reported(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "vendored").symlink_to(tmp_path / "no-such-target")
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert any("vendored is a symlinked directory" in p for p in response.problems)


def test_a_declaration_that_is_a_directory_is_a_problem_not_a_crash(
    tmp_path: Path,
) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").unlink()
    (tmp_path / "appone" / ".tesser-root").mkdir()
    response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    assert any("appone/.tesser-root is missing" in p for p in response.problems)


def test_a_nonexistent_root_is_a_problem_not_a_crash(tmp_path: Path) -> None:
    response = wire.build().check(
        client.CheckRequest(root=str(tmp_path / "no-such-dir"))
    )
    assert len(response.problems) == 1
    assert "is not a directory" in response.problems[0]


def test_an_unlistable_directory_does_not_crash(tmp_path: Path) -> None:
    import os

    _repo(tmp_path)
    locked = tmp_path / "appone" / "locked"
    locked.mkdir()
    os.chmod(locked, 0)
    try:
        response = wire.build().check(client.CheckRequest(root=str(tmp_path)))
    finally:
        os.chmod(locked, 0o755)
    assert response.problems == ()
