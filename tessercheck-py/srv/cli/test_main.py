from __future__ import annotations

from pathlib import Path

import pytest

from app.loader import load
from srv.cli.main import run


def test_a_clean_tree_runs_to_exit_code_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    assert run([str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_a_finding_runs_to_exit_code_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run([str(tmp_path)]) == 1
    assert "TB044" in capsys.readouterr().out


def test_the_app_closes_idempotently(tmp_path: Path) -> None:
    app = load()
    app.close()
    app.close()


def test_a_usage_error_becomes_exit_code_two_with_the_usage_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    assert run([str(tmp_path), "surplus"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unexpected extra arguments" in captured.err
    assert "usage: python -m srv.cli.main" in captured.err


def test_the_host_never_leaks_internals_on_the_unexpected_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    assert run([f"{tmp_path}/"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "trailing separator" not in captured.err
    assert captured.err == "unexpected error\n"
