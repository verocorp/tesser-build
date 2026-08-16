from __future__ import annotations

import pytest

import reports.application.ports.link_source as link_source
import reports.application.ports.verdict_source as verdict_source
import reports.application.views as views
import reports.domain.report as report
from tesser.errors import DomainError


def test_domain_links_carries_every_record_into_a_domain_link() -> None:
    listed = link_source.ListLinksResponse(
        links=(
            link_source.LinkRecord(slug="spring-sale", target_url="https://a.example/s"),
            link_source.LinkRecord(slug="winter-sale", target_url="https://a.example/w"),
        )
    )

    links = views.domain_links(listed)

    assert [str(link.slug) for link in links] == ["spring-sale", "winter-sale"]
    assert [str(link.target_url) for link in links] == [
        "https://a.example/s",
        "https://a.example/w",
    ]


def test_domain_links_turns_an_empty_listing_into_no_links() -> None:
    assert views.domain_links(link_source.ListLinksResponse(links=())) == ()


def test_domain_links_refuses_a_record_the_domain_would_not_accept() -> None:
    listed = link_source.ListLinksResponse(
        links=(link_source.LinkRecord(slug="spring-sale", target_url="not-a-url"),)
    )

    with pytest.raises(DomainError):
        views.domain_links(listed)


def test_domain_verdicts_reads_the_allowed_member_as_an_allowed_decision() -> None:
    listed = verdict_source.ListVerdictsResponse(
        verdicts=(
            verdict_source.VerdictRecord(
                target_url="https://a.example/s",
                decision=verdict_source.VerdictDecision.ALLOWED,
                reason="on the allowlist",
            ),
        )
    )

    verdicts = views.domain_verdicts(listed)

    assert str(verdicts[0].allowed) == "allowed"
    assert str(verdicts[0].reason) == "on the allowlist"


def test_domain_verdicts_reads_the_denied_member_as_a_denied_decision() -> None:
    listed = verdict_source.ListVerdictsResponse(
        verdicts=(
            verdict_source.VerdictRecord(
                target_url="https://a.example/s",
                decision=verdict_source.VerdictDecision.DENIED,
                reason="host blocked",
            ),
        )
    )

    verdicts = views.domain_verdicts(listed)

    assert str(verdicts[0].allowed) == "denied"


def test_domain_verdicts_refuses_a_record_carrying_no_reason() -> None:
    listed = verdict_source.ListVerdictsResponse(
        verdicts=(
            verdict_source.VerdictRecord(
                target_url="https://a.example/s",
                decision=verdict_source.VerdictDecision.ALLOWED,
                reason="",
            ),
        )
    )

    with pytest.raises(DomainError):
        views.domain_verdicts(listed)


def test_links_by_verdict_response_flattens_a_row_into_primitives() -> None:
    rows = (
        report.LinkVerdict(
            slug="spring-sale",
            target_url="https://a.example/s",
            allowed=False,
            reason="host blocked",
        ),
    )

    resp = views.links_by_verdict_response(rows)

    assert resp.links[0].slug == "spring-sale"
    assert resp.links[0].target_url == "https://a.example/s"
    assert resp.links[0].allowed is False
    assert resp.links[0].reason == "host blocked"


def test_links_by_verdict_response_reads_an_allowed_row_as_a_true_flag() -> None:
    rows = (
        report.LinkVerdict(
            slug="spring-sale",
            target_url="https://a.example/s",
            allowed=True,
            reason="on the allowlist",
        ),
    )

    resp = views.links_by_verdict_response(rows)

    assert resp.links[0].allowed is True


def test_links_by_verdict_response_preserves_the_order_it_was_handed() -> None:
    rows = (
        report.LinkVerdict("winter-sale", "https://a.example/w", False, "host blocked"),
        report.LinkVerdict("spring-sale", "https://a.example/s", True, "on the allowlist"),
    )

    resp = views.links_by_verdict_response(rows)

    assert [view.slug for view in resp.links] == ["winter-sale", "spring-sale"]


def test_links_by_verdict_response_turns_no_rows_into_no_views() -> None:
    assert views.links_by_verdict_response(()).links == ()
