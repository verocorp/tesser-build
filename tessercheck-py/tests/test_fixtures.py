from __future__ import annotations

import pathlib


def test_tb031_fixture_pair_holds_its_contract_before_the_checker_ships() -> None:
    d = pathlib.Path(__file__).resolve().parent.parent / "testdata" / "tb031"
    good = (d / "good_tree" / "test_shortlink.py").read_text(encoding="utf-8")
    bad = (d / "bad_tree" / "test_shortlink.py").read_text(encoding="utf-8")
    assert good != bad, "tb031 fixtures converged — the pair no longer specifies a violation"
    assert (d / "good_tree" / "shortlink.py").read_text(encoding="utf-8") == (
        d / "bad_tree" / "shortlink.py"
    ).read_text(encoding="utf-8"), (
        "tb031 fixture subjects diverged — the pair must differ only in the test file"
    )
