from __future__ import annotations

from pathlib import Path

import tessercheck.adapters.repositories.source_reader as source_repository
import tessercheck.application.ports.source_reader as source_reader


def test_a_declared_tree_reads_as_an_app(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.APP
    assert read.sources == ()
    assert read.nested == ()
    assert read.symlinked == ()
    assert "os" in read.stdlib


def test_a_tree_with_no_declaration_reads_as_missing(tmp_path: Path) -> None:
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.MISSING


def test_a_declaration_that_does_not_open_with_app_reads_as_unrecognized(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("library\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.UNRECOGNIZED


def test_an_undecodable_declaration_reads_as_unreadable(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_bytes(b"\xff\xfe\x00app")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.UNREADABLE


def test_a_bom_prefixed_declaration_still_reads_as_an_app(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.APP


def test_export_and_import_directives_are_carried_through(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text(
        "app\nexport tesser\nimport other.client.client\n", encoding="utf-8"
    )
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.exports == ("tesser",)
    assert read.imports == ("other.client.client",)


def test_a_directive_with_no_value_makes_the_declaration_unrecognized(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.UNRECOGNIZED


def test_a_skip_naming_a_path_makes_the_declaration_unrecognized(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip a/b\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.root is source_reader.RootForm.UNRECOGNIZED


def test_a_skipped_directory_is_not_walked(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip testdata\n", encoding="utf-8")
    (tmp_path / "testdata").mkdir()
    (tmp_path / "testdata" / "broken.py").write_text("def f(:\n", encoding="utf-8")
    (tmp_path / "kept.py").write_text("x = 1\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert [source.path for source in read.sources] == ["kept.py"]


def test_the_standard_noise_directories_are_not_walked(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "kept.py").write_text("x = 1\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert [source.path for source in read.sources] == ["kept.py"]


def test_sources_come_back_sorted_by_path_with_their_module_names(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "zebra.py").write_text("z = 1\n", encoding="utf-8")
    (tmp_path / "app" / "alpha.pyi").write_text("a: int\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert [(source.path, source.name) for source in read.sources] == [
        ("app/__init__.py", "app"),
        ("app/alpha.pyi", "app.alpha"),
        ("app/zebra.py", "app.zebra"),
    ]


def test_an_init_reads_as_a_package_and_a_module_reads_as_a_module(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "thing.py").write_text("x = 1\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    forms = {source.name: source.form for source in read.sources}
    assert forms["app"] is source_reader.ModuleForm.PACKAGE
    assert forms["app.thing"] is source_reader.ModuleForm.MODULE


def test_a_root_level_init_carries_no_module_name_and_is_dropped(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "kept.py").write_text("x = 1\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert [source.path for source in read.sources] == ["kept.py"]


def test_a_readable_source_carries_its_text_and_a_read_state(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "thing.py").write_bytes(b"\xef\xbb\xbfx = 1\n")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.sources[0].state is source_reader.SourceState.READ
    assert read.sources[0].text == "x = 1\n"


def test_an_undecodable_source_carries_no_text_and_an_unreadable_state(
    tmp_path: Path,
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "thing.py").write_bytes(b"\xff\xfe\x00x")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.sources[0].state is source_reader.SourceState.UNREADABLE
    assert read.sources[0].text == ""


def test_a_declaration_below_the_root_is_reported_as_nested(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "inner").mkdir()
    (tmp_path / "inner" / ".tesser-root").write_text("app\n", encoding="utf-8")
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.nested == ("inner/.tesser-root",)


def test_a_symlinked_directory_is_reported_and_never_walked(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "smuggled.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "vendored").symlink_to(outside)
    read = source_repository.FilesystemSourceReader().sources(
        source_reader.ReadSourcesRequest(tree=str(tmp_path))
    )
    assert read.symlinked == ("vendored",)
    assert read.sources == ()
