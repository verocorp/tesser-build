from __future__ import annotations

import pathlib

import pytest

import srv.cli.rules as rules


def test_a_usage_error_becomes_exit_code_two_with_the_usage_line(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    assert rules.RulesHost().run([str(tmp_path), "surplus"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unexpected extra arguments" in captured.err
    assert "usage: python -m srv.cli.rules" in captured.err
    assert not (tmp_path / "RULES.md").exists()


def test_the_host_never_leaks_internals_on_the_unexpected_path(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    assert rules.RulesHost().run([f"{tmp_path}/"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "trailing separator" not in captured.err
    assert captured.err == "unexpected error\n"


def test_a_tree_renders_the_rulebook_into_the_output(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    assert rules.RulesHost().run([str(tmp_path)]) == 0
    assert "wrote " in capsys.readouterr().out
    rendered = (tmp_path / "RULES.md").read_text()
    assert rendered.startswith("# Rules implemented in the spike")
    assert "| TB020 | the rendered tail | every module | a shape |" in rendered


def test_rendering_replaces_a_stale_output(tmp_path: pathlib.Path) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    (tmp_path / "RULES.md").write_text("| an old row |\n")
    assert rules.RulesHost().run([str(tmp_path)]) == 0
    assert "| an old row |" not in (tmp_path / "RULES.md").read_text()


def test_checking_a_matching_output_settles_at_zero(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    assert rules.RulesHost().run([str(tmp_path)]) == 0
    capsys.readouterr()
    assert rules.RulesHost().run([str(tmp_path), "--check"]) == 0
    assert "RULES.md is current" in capsys.readouterr().out


def test_checking_a_stale_output_settles_at_one(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    (tmp_path / "RULES.md").write_text("| an old row |\n")
    assert rules.RulesHost().run([str(tmp_path), "--check"]) == 1
    assert "RULES.md is stale" in capsys.readouterr().err
    assert (tmp_path / "RULES.md").read_text() == "| an old row |\n"


def test_checking_a_missing_output_settles_at_one(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text("")
    (tmp_path / ".importlinter").write_text("")
    assert rules.RulesHost().run([str(tmp_path), "--check"]) == 1
    assert "RULES.md is stale" in capsys.readouterr().err
    assert not (tmp_path / "RULES.md").exists()
