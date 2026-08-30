from __future__ import annotations

import os
import pathlib

import tesser.testing as ts

import repo.adapters.repositories.file_repository as file_repository
import repo.application.ports.repo_reader as repo_reader


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
    return root


def test_a_repo_reads_whole(tmp_path: pathlib.Path) -> None:
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(_repo(tmp_path))))
    assert read.manifest.state is repo_reader.ManifestState.READ
    assert [(row.key, row.kind) for row in read.manifest.rows] == [("appone", "app")]
    assert read.verify.state is repo_reader.FileState.READ
    assert "run_appone" in read.verify.text
    assert read.workflow.state is repo_reader.FileState.READ
    assert read.requirements == ("appone",)


def test_a_missing_manifest_reports_missing(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").unlink()
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.manifest.state is repo_reader.ManifestState.MISSING
    assert read.manifest.rows == ()


def test_a_malformed_manifest_reports_malformed_with_the_parse_note(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text("{ truncated")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.manifest.state is repo_reader.ManifestState.MALFORMED
    assert read.manifest.note != ""


def test_a_misshapen_manifest_reports_misshapen(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_text('["a", "b"]')
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.manifest.state is repo_reader.ManifestState.MISSHAPEN


def test_a_missing_verify_file_reports_missing(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "scripts" / "verify").unlink()
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.verify.state is repo_reader.FileState.MISSING


def test_entries_mark_directories_and_symlinks(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "vendored").symlink_to(outside)
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    forms = {entry.name: entry.form for entry in read.top}
    assert forms["appone"] is repo_reader.EntryForm.DIRECTORY
    assert forms["vendored"] is repo_reader.EntryForm.SYMLINK


def test_entries_keep_github_and_drop_other_hidden_and_skip_dirs(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".hidden").mkdir()
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    names = {entry.name for entry in read.top}
    assert ".github" in names
    assert ".venv" not in names
    assert ".hidden" not in names


def test_the_walk_reports_declarations_with_relative_paths(tmp_path: pathlib.Path) -> None:
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(_repo(tmp_path))))
    assert [(record.path, record.state) for record in read.declarations] == [
        ("appone/.tesser-root", repo_reader.FileState.READ)
    ]
    assert read.declarations[0].text == "app\n"


def test_a_bom_prefixed_declaration_decodes(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.declarations[0].text == "app\n"


def test_an_undecodable_declaration_reports_unreadable(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").write_bytes(b"\xff\xfe\x00app")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.declarations[0].state is repo_reader.FileState.UNREADABLE


def test_a_declaration_that_is_a_directory_is_not_a_declaration(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / ".tesser-root").unlink()
    (tmp_path / "appone" / ".tesser-root").mkdir()
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.declarations == ()


def test_the_walk_finds_requirements_at_depth(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    deep = tmp_path / "docs" / "buried" / "tree"
    deep.mkdir(parents=True)
    (deep / "requirements-dev.txt").write_text("pytest\n")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert "docs/buried/tree" in read.requirements


def test_the_walk_skips_ignored_directories(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    hidden = tmp_path / "appone" / ".venv"
    hidden.mkdir()
    (hidden / ".tesser-root").write_text("app\n")
    (hidden / "requirements-dev.txt").write_text("x\n")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert [record.path for record in read.declarations] == ["appone/.tesser-root"]
    assert read.requirements == ("appone",)


def test_the_walk_never_follows_symlinked_directories(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-smuggle"
    outside.mkdir()
    (outside / ".tesser-root").write_text("app\n")
    (outside / "requirements-dev.txt").write_text("x\n")
    (tmp_path / "appone" / "vendored").symlink_to(outside)
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert [record.path for record in read.declarations] == ["appone/.tesser-root"]
    assert read.requirements == ("appone",)


def test_a_dangling_symlink_does_not_crash_the_walk(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "appone" / "vendored").symlink_to(tmp_path / "no-such-target")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.manifest.state is repo_reader.ManifestState.READ


def test_an_unlistable_directory_does_not_crash_the_walk(tmp_path: pathlib.Path) -> None:
    if os.geteuid() == 0:
        return
    _repo(tmp_path)
    locked = tmp_path / "appone" / "locked"
    locked.mkdir()
    os.chmod(locked, 0)
    try:
        reader = file_repository.FilesystemRepoReader()
        read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    finally:
        os.chmod(locked, 0o755)
    assert read.manifest.state is repo_reader.ManifestState.READ


def test_a_top_level_dangling_symlink_is_an_entry_with_symlink_form(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "vendored").symlink_to(tmp_path / "no-such-target")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    forms = {entry.name: entry.form for entry in read.top}
    assert forms["vendored"] is repo_reader.EntryForm.SYMLINK


def test_an_undecodable_manifest_reports_unreadable(tmp_path: pathlib.Path) -> None:
    _repo(tmp_path)
    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe\x00{}")
    reader = file_repository.FilesystemRepoReader()
    read = reader.read(repo_reader.ReadRepoRequest(repo_root=str(tmp_path)))
    assert read.manifest.state is repo_reader.ManifestState.UNREADABLE
    assert read.manifest.rows == ()
