from __future__ import annotations

import reports.domain.report as report


def test_join_semantics_default_and_ordering() -> None:
    links = (report.Link("z", "https://ok.example/z"), report.Link("a", "https://bad.example/a"))
    verdicts = (report.RecordedVerdict("https://bad.example/a", False, "host blocked"),)
    rows = report.join_links_with_verdicts(links, verdicts)
    assert [str(r.slug) for r in rows] == ["a", "z"]
    assert str(rows[0].allowed) == "denied" and str(rows[0].reason) == "host blocked"
    assert str(rows[1].allowed) == "allowed" and str(rows[1].reason) == "no verdict recorded"
