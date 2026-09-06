from __future__ import annotations

import os
import pathlib

import tesser.testing as ts

import repo.adapters.repositories as repositories
import repo.application.ports as ports


@ts.helper
def _repo(root: pathlib.Path) -> pathlib.Path:  # tesser:debt TB073
    (root / "manifest.json").write_text('{"appone": "app"}')
    (root / "scripts").mkdir()
    (root / "scripts" / "verify").write_text("run_appone() {\n}\n")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "test.yml").write_text("jobs:\n")
    (root / "appone").mkdir()
    (root / "appone" / ".tesser-root").write_text("app\n")
    (root / "appone" / "requirements-dev.txt").write_text("pytest\n")
    (root / "appone" / "pyproject.toml").write_text(
        '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'
    )
    (root / "appone" / "ruff.toml").write_text('target-version = "py312"\n')
    return root


def test_a_repo_reads_whole(tmp_path: pathlib.Path) -> None:
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(_repo(tmp_path))))
    assert read_repo_response.manifest.state is ports.ManifestState.READ
    assert [(row.key, row.kind) for row in read_repo_response.manifest.rows] == [("appone", "app")]
    assert read_repo_response.verify.state is ports.FileState.READ
    assert "run_appone" in read_repo_response.verify.text
    assert read_repo_response.workflow.state is ports.FileState.READ
    assert read_repo_response.requirements == ("appone",)


def test_a_missing_manifest_reports_missing(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").unlink()
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.manifest.state is ports.ManifestState.MISSING
    assert read_repo_response.manifest.rows == ()


def test_a_malformed_manifest_reports_malformed_with_the_parse_note(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.manifest.state is ports.ManifestState.MALFORMED
    assert read_repo_response.manifest.note != ""


def test_a_misshapen_manifest_reports_misshapen(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text('["a", "b"]')
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.manifest.state is ports.ManifestState.MISSHAPEN


def test_a_missing_verify_file_reports_missing(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "scripts" / "verify").unlink()
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.verify.state is ports.FileState.MISSING


def test_entries_mark_directories_and_symlinks(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "vendored").symlink_to(outside)
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    forms = {entry.name: entry.form for entry in read_repo_response.top}
    assert forms["appone"] is ports.EntryForm.DIRECTORY
    assert forms["vendored"] is ports.EntryForm.SYMLINK


def test_entries_keep_github_and_drop_other_hidden_and_skip_dirs(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".hidden").mkdir()
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    names = {entry.name for entry in read_repo_response.top}
    assert ".github" in names
    assert ".venv" not in names
    assert ".hidden" not in names


def test_the_walk_reports_declarations_with_relative_paths(tmp_path: pathlib.Path) -> None:
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(_repo(tmp_path))))
    assert [(record.path, record.state) for record in read_repo_response.declarations] == [
        ("appone/.tesser-root", ports.FileState.READ)
    ]
    assert read_repo_response.declarations[0].text == "app\n"


def test_a_bom_prefixed_declaration_decodes(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.declarations[0].text == "app\n"


def test_an_undecodable_declaration_reports_unreadable(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_bytes(b"\xff\xfe\x00app")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.declarations[0].state is ports.FileState.UNREADABLE


def test_a_declaration_that_is_a_directory_is_not_a_declaration(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").unlink()
    (tmp_path / "appone" / ".tesser-root").mkdir()
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.declarations == ()


def test_the_walk_finds_requirements_at_depth(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    deep = tmp_path / "docs" / "buried" / "tree"
    deep.mkdir(parents=True)
    (deep / "requirements-dev.txt").write_text("pytest\n")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert "docs/buried/tree" in read_repo_response.requirements


def test_the_walk_skips_ignored_directories(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    hidden = tmp_path / "appone" / ".venv"
    hidden.mkdir()
    (hidden / ".tesser-root").write_text("app\n")
    (hidden / "requirements-dev.txt").write_text("x\n")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert [record.path for record in read_repo_response.declarations] == ["appone/.tesser-root"]
    assert read_repo_response.requirements == ("appone",)


def test_the_walk_never_follows_symlinked_directories(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-smuggle"
    outside.mkdir()
    (outside / ".tesser-root").write_text("app\n")
    (outside / "requirements-dev.txt").write_text("x\n")
    (tmp_path / "appone" / "vendored").symlink_to(outside)
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert [record.path for record in read_repo_response.declarations] == ["appone/.tesser-root"]
    assert read_repo_response.requirements == ("appone",)


def test_a_dangling_symlink_does_not_crash_the_walk(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "vendored").symlink_to(tmp_path / "no-such-target")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.manifest.state is ports.ManifestState.READ


def test_an_unlistable_directory_does_not_crash_the_walk(tmp_path: pathlib.Path) -> None:
    if os.geteuid() == 0:
        return
    _repo(tmp_path)
    locked = tmp_path / "appone" / "locked"
    locked.mkdir()
    os.chmod(locked, 0)
    try:
        filesystem_repo_reader = repositories.FilesystemRepoReader()
        read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    finally:
        os.chmod(locked, 0o755)
    assert read_repo_response.manifest.state is ports.ManifestState.READ


def test_a_top_level_dangling_symlink_is_an_entry_with_symlink_form(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "vendored").symlink_to(tmp_path / "no-such-target")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    forms = {entry.name: entry.form for entry in read_repo_response.top}
    assert forms["vendored"] is ports.EntryForm.SYMLINK


def test_an_undecodable_manifest_reports_unreadable(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe\x00{}")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read_repo_response.manifest.state is ports.ManifestState.UNREADABLE
    assert read_repo_response.manifest.rows == ()


def test_the_walk_reads_the_stated_python_floors(tmp_path: pathlib.Path) -> None:
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(_repo(tmp_path))))
    stated = {(record.path, record.key, record.state, record.value) for record in read_repo_response.floors}
    assert stated == {
        (
            "appone/pyproject.toml",
            ports.FloorKey.REQUIRES_PYTHON,
            ports.FloorState.READ,
            ">=3.12",
        ),
        (
            "appone/ruff.toml",
            ports.FloorKey.TARGET_VERSION,
            ports.FloorState.READ,
            "py312",
        ),
    }


def test_a_pyproject_without_a_project_table_states_no_floor(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n"
    )
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    assert [record.path for record in read_repo_response.floors] == ["appone/ruff.toml"]


def test_a_project_table_without_requires_python_reports_undeclared(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "pyproject.toml").write_text('[project]\nname = "appone"\n')
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    states = {record.path: record.state for record in read_repo_response.floors}
    assert states["appone/pyproject.toml"] is ports.FloorState.UNDECLARED


def test_a_pyproject_ruff_table_states_the_target_version(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "ruff.toml").unlink()
    (tmp_path / "appone" / "pyproject.toml").write_text(
        '[project]\nname = "appone"\nrequires-python = ">=3.12"\n'
        '[tool.ruff]\ntarget-version = "py312"\n'
    )
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    keys = {record.key: record.value for record in read_repo_response.floors}
    assert keys[ports.FloorKey.TARGET_VERSION] == "py312"


def test_a_malformed_toml_reports_malformed(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "ruff.toml").write_text("target-version = \n")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    states = {record.path: record.state for record in read_repo_response.floors}
    assert states["appone/ruff.toml"] is ports.FloorState.MALFORMED


def test_an_undecodable_toml_reports_unreadable(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "ruff.toml").write_bytes(b"\xff\xfe\x00x")
    filesystem_repo_reader = repositories.FilesystemRepoReader()
    read_repo_response = filesystem_repo_reader.read(ports.ReadRepoRequest(repo_root=str(tmp_path)))
    states = {record.path: record.state for record in read_repo_response.floors}
    assert states["appone/ruff.toml"] is ports.FloorState.UNREADABLE
