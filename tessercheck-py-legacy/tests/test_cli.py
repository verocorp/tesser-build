"""CLI tests — the --select/--ignore code filters that make the enforcement
ratchet operable (blocking vs advisory tiers are two CI jobs with different
code lists; demoting a wrong check is a one-line list edit, never an inline
suppression in consumer code).

Fixtures are copied to a tmp path first: the CLI's default scoping exempts
``testdata/`` paths as test code, so running it on the fixture in place would
prove nothing.
"""

from pathlib import Path

import pytest

from tessercheck.cli import main

_TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


@pytest.fixture()
def bad_domain_file(tmp_path: Path) -> str:
    src = (_TESTDATA / "tb001" / "bad.py").read_text(encoding="utf-8")
    target = tmp_path / "values.py"
    target.write_text(src, encoding="utf-8")
    return str(target)


def _codes_in_output(out: str) -> set[str]:
    return {word for line in out.splitlines() for word in line.split() if word.startswith("TB")}


def test_select_limits_to_named_codes(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["--select", "TB001", bad_domain_file])
    out = capsys.readouterr().out
    assert rc == 1
    emitted = _codes_in_output(out)
    assert emitted == {"TB001"}


def test_select_other_code_silences_findings(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["--select", "TB004", bad_domain_file])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == ""


def test_ignore_removes_named_code(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc_all = main([bad_domain_file])
    all_codes = _codes_in_output(capsys.readouterr().out)
    assert rc_all == 1 and "TB001" in all_codes

    main(["--ignore", "TB001", bad_domain_file])
    remaining = _codes_in_output(capsys.readouterr().out)
    assert "TB001" not in remaining


def test_ignore_applies_after_select(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["--select", "TB001", "--ignore", "TB001", bad_domain_file])
    assert rc == 0
    assert capsys.readouterr().out.strip() == ""


def test_unknown_code_is_a_loud_usage_error(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--select", "TB999", bad_domain_file])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "TB999" in err and "registered" in err


def test_empty_code_list_is_a_usage_error(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--select", ",", bad_domain_file])
    assert exc.value.code == 2
    assert "no check codes" in capsys.readouterr().err


def test_lowercase_codes_accepted(
    bad_domain_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["--select", "tb001", bad_domain_file])
    out = capsys.readouterr().out
    assert rc == 1
    assert "TB001" in out
