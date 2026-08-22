from __future__ import annotations

import pytest

from srv.cli.main import CliHost


def test_a_domain_rejection_becomes_an_exit_code_not_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = CliHost().run(["create-campaign", "-5", "USD"])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert captured.err.startswith("[")


def test_a_missing_argument_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = CliHost().run(["create-campaign", "100.00"])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage: create-campaign" in captured.err


def test_an_empty_argument_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = CliHost().run(["create-campaign", "", "USD"])
    captured = capsys.readouterr()
    assert code == 2
    assert "missing argument <budget_amount>" in captured.err


def test_extra_arguments_are_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = CliHost().run(["create-campaign", "100.00", "USD", "surplus"])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage: create-campaign" in captured.err


def test_a_lookup_that_finds_nothing_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    code = CliHost().run(["add-link", "0123456789abcdef", "promo", "https://a.example/p"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err.startswith("[")


def test_an_unknown_command_is_answered_with_the_banner(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = CliHost().run(["nope"])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage: python -m srv.cli.main" in captured.err


def test_no_command_is_answered_with_the_banner(capsys: pytest.CaptureFixture[str]) -> None:
    code = CliHost().run([])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage: python -m srv.cli.main" in captured.err


def test_each_campaign_command_is_wired_to_its_own_handler(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in ("create-campaign", "add-link", "deactivate-link"):
        assert CliHost().run([name]) == 2
        assert f"usage: {name}" in capsys.readouterr().err


def test_create_campaign_reaches_the_campaign_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = CliHost().run(["create-campaign", "100.00", "USD"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("created campaign ")
    assert captured.err == ""
