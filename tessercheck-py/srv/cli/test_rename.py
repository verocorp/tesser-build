from __future__ import annotations

import pathlib

import pytest

import srv.cli as cli


def test_a_local_named_for_nothing_is_renamed_in_place(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod" / "domain").mkdir(parents=True)
    (tmp_path / "mod" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "mod" / "domain" / "__init__.py").write_text(
        "from mod.domain.tag import Tag as Tag\n"
        "from mod.domain.tag import TagSpec as TagSpec\n",
        encoding="utf-8",
    )
    (tmp_path / "mod" / "domain" / "tag.py").write_text(
        "import tesser.domain as ts\n"
        "class TagSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, spec: TagSpec) -> None:\n"
        "        object.__setattr__(self, '_text', spec.text)\n",
        encoding="utf-8",
    )
    sibling = tmp_path / "mod" / "domain" / "test_tag.py"
    sibling.write_text(
        "import mod.domain as domain\n"
        "def test_a_tag_is_built_from_its_spec() -> None:\n"
        "    made = domain.TagSpec('a')\n"
        "    assert domain.Tag(made) is not None\n",
        encoding="utf-8",
    )
    cli.RenameHost().run([str(tmp_path)])
    captured = capsys.readouterr()
    assert "renamed 1 file(s)" in captured.out
    assert "tag_spec = domain.TagSpec('a')" in sibling.read_text(encoding="utf-8")
    assert "domain.Tag(tag_spec) is not None" in sibling.read_text(encoding="utf-8")


def test_a_usage_error_becomes_exit_code_two_and_rewrites_nothing(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    (tmp_path / "mod" / "domain").mkdir(parents=True)
    (tmp_path / "mod" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "mod" / "domain" / "__init__.py").write_text(
        "from mod.domain.tag import TagSpec as TagSpec\n", encoding="utf-8"
    )
    (tmp_path / "mod" / "domain" / "tag.py").write_text(
        "import tesser.domain as ts\n"
        "class TagSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
        encoding="utf-8",
    )
    sibling = tmp_path / "mod" / "domain" / "test_tag.py"
    sibling.write_text(
        "import mod.domain as domain\n"
        "def test_a_spec_carries_its_text() -> None:\n"
        "    made = domain.TagSpec('a')\n"
        "    assert made.text == 'a'\n",
        encoding="utf-8",
    )
    before = sibling.read_text(encoding="utf-8")
    assert cli.RenameHost().run([str(tmp_path), "surplus"]) == 2
    captured = capsys.readouterr()
    assert "unexpected extra arguments" in captured.err
    assert "usage: python -m srv.cli.rename" in captured.err
    assert sibling.read_text(encoding="utf-8") == before
