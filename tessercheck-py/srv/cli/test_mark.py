from __future__ import annotations

import pathlib

import pytest

import srv.cli as cli


def test_every_code_reported_on_a_line_comes_back_in_one_marker(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod" / "domain").mkdir(parents=True)
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text("import mod.domain.tag as tag\n", encoding="utf-8")
    (tmp_path / "mod" / "domain" / "__init__.py").write_text(
        "from mod.domain.tag import Tag as Tag\n", encoding="utf-8"
    )
    (tmp_path / "mod" / "domain" / "tag.py").write_text(
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, value: str) -> None:\n"
        '        object.__setattr__(self, "_value", value)\n',
        encoding="utf-8",
    )
    (tmp_path / "mod" / "domain" / "test_tag.py").write_text(
        "import mod.domain as domain\n"
        "def test_a_tag_holds_its_value() -> None:\n"
        '    assert domain.Tag("a") is not None\n',
        encoding="utf-8",
    )
    assert cli.MarkHost().run([str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "marked 1 file(s)" in captured.out
    assert "cannot mark" not in captured.out
    assert marked.read_text(encoding="utf-8") == (
        "import mod.domain.tag as tag  # tesser:debt TB042 TB060\n"
    )


def test_a_marked_tree_comes_back_clean_and_a_second_run_writes_nothing(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod" / "domain").mkdir(parents=True)
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text("import mod.domain.tag as tag\n", encoding="utf-8")
    (tmp_path / "mod" / "domain" / "__init__.py").write_text(
        "from mod.domain.tag import Tag as Tag\n", encoding="utf-8"
    )
    (tmp_path / "mod" / "domain" / "tag.py").write_text(
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, value: str) -> None:\n"
        '        object.__setattr__(self, "_value", value)\n',
        encoding="utf-8",
    )
    (tmp_path / "mod" / "domain" / "test_tag.py").write_text(
        "import mod.domain as domain\n"
        "def test_a_tag_holds_its_value() -> None:\n"
        '    assert domain.Tag("a") is not None\n',
        encoding="utf-8",
    )
    cli.MarkHost().run([str(tmp_path)])
    capsys.readouterr()
    once = marked.read_text(encoding="utf-8")
    assert cli.MarkHost().run([str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "marked 0 file(s)" in captured.out
    assert marked.read_text(encoding="utf-8") == once


def test_a_marker_the_line_already_carries_is_widened_never_repeated(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod" / "domain").mkdir(parents=True)
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text(
        "import mod.domain.tag as tag  # tesser:debt TB060\n", encoding="utf-8"
    )
    (tmp_path / "mod" / "domain" / "__init__.py").write_text(
        "from mod.domain.tag import Tag as Tag\n", encoding="utf-8"
    )
    (tmp_path / "mod" / "domain" / "tag.py").write_text(
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, value: str) -> None:\n"
        '        object.__setattr__(self, "_value", value)\n',
        encoding="utf-8",
    )
    (tmp_path / "mod" / "domain" / "test_tag.py").write_text(
        "import mod.domain as domain\n"
        "def test_a_tag_holds_its_value() -> None:\n"
        '    assert domain.Tag("a") is not None\n',
        encoding="utf-8",
    )
    assert cli.MarkHost().run([str(tmp_path)]) == 0
    capsys.readouterr()
    assert marked.read_text(encoding="utf-8") == (
        "import mod.domain.tag as tag  # tesser:debt TB042 TB060\n"
    )


def test_a_finding_on_a_line_the_module_has_not_got_is_reported_not_written(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod").mkdir()
    homeless = tmp_path / "mod" / "__init__.py"
    homeless.write_text("", encoding="utf-8")
    assert cli.MarkHost().run([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "marked 0 file(s)" in captured.out
    assert "1 finding(s) this cannot mark:" in captured.out
    assert "TB040" in captured.out
    assert homeless.read_text(encoding="utf-8") == ""


def test_a_usage_error_becomes_exit_code_two_and_marks_nothing(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod").mkdir()
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text("import mod.domain.tag as tag\n", encoding="utf-8")
    before = marked.read_text(encoding="utf-8")
    assert cli.MarkHost().run([str(tmp_path), "surplus"]) == 2
    captured = capsys.readouterr()
    assert "unexpected extra arguments" in captured.err
    assert "usage: python -m srv.cli.mark" in captured.err
    assert marked.read_text(encoding="utf-8") == before


def test_an_undeclared_tree_is_reported_and_nothing_is_written(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "mod").mkdir()
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text("import mod.domain.tag as tag\n", encoding="utf-8")
    assert cli.MarkHost().run([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "marked 0 file(s)" in captured.out
    assert "TB044" in captured.out
    assert marked.read_text(encoding="utf-8") == "import mod.domain.tag as tag\n"


def test_the_host_never_leaks_internals_on_the_unexpected_path(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod").mkdir()
    marked = tmp_path / "mod" / "__init__.py"
    marked.write_text("import mod.domain.tag as tag\n", encoding="utf-8")
    assert cli.MarkHost().run([f"{tmp_path}/"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "trailing separator" not in captured.err
    assert captured.err == "unexpected error\n"
    assert marked.read_text(encoding="utf-8") == "import mod.domain.tag as tag\n"
