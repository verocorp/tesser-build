from __future__ import annotations

import alpha.application.mapping as mapping
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.whole_repository as whole_repository
import alpha.domain.thing as thing


def test_an_absent_lookup_maps_to_no_views() -> None:
    found = whole_repository.FindWholeResponse(outcome=whole_repository.Lookup.ABSENT, wholes=())
    assert mapping.MapToGetResponse(found=found).wholes == ()


def test_a_refused_check_maps_to_no_views() -> None:
    whole = thing.Whole(thing.WholeSpec("w", thing.PairSpec("a", 1), (), "o"))
    checked = beta_check.CheckResponse(verdict=beta_check.Verdict.REFUSED)
    assert mapping.MapToAddResponse(whole=whole, checked=checked).wholes == ()
