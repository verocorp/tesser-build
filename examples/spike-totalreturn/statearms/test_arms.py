"""Assert the wins; don't narrate them.

v2 business rules -- a third state, "suspended for billing", arrives:

    serve the redirect?  no
    public message?      "This link is temporarily suspended."  (NOT "no longer available")
    counts toward quota? YES -- a suspended link still occupies its slug

A SILENT SITE is a consumer that still runs, still passes its v1 test, and is
now wrong. That is the metric docs/design-three-contender-changeability.md
already uses; this file applies it to the enum-vs-value-object question.

Run: PYTHONPATH=tesser-py python3 -m pytest examples/spike-totalreturn/statearms -q
"""

from __future__ import annotations

try:
    import pytest
except ModuleNotFoundError:  # sandbox has no pytest; the assertions still run
    import contextlib
    import types

    @contextlib.contextmanager
    def _raises(exc):
        try:
            yield
        except exc:
            return
        raise AssertionError(f"expected {exc.__name__}")

    pytest = types.SimpleNamespace(raises=_raises)

import arm_bool
import arm_enum
import arm_vo

SUSPENDED_MESSAGE = "This link is temporarily suspended."


# --- Arm 1: bool ------------------------------------------------------------

def test_bool_arm_cannot_represent_a_third_state_without_a_second_flag() -> None:
    # The third state needs a second field, and the two fields do not constrain
    # each other: "active and suspended" is constructible and meaningless.
    nonsense = arm_bool.ShortLink("promo", active=True, suspended=True)
    assert nonsense.active and nonsense.suspended
    # Worse than wrong output -- it silently serves a suspended link.
    assert arm_bool.should_redirect(nonsense) is True


def test_bool_arm_has_two_silent_sites() -> None:
    link = arm_bool.ShortLink("promo", active=False, suspended=True)

    assert arm_bool.should_redirect(link) is False  # correct, by luck

    # SILENT SITE 1: tells the visitor the link is gone forever.
    assert arm_bool.public_message(link) != SUSPENDED_MESSAGE

    # SILENT SITE 2: stops billing for a slug that is still occupied.
    assert arm_bool.counts_toward_quota(link) is False


# --- Arm 2: enum ------------------------------------------------------------

def test_enum_arm_has_one_silent_site_and_one_accidental_pass() -> None:
    link = arm_enum.ShortLink("promo", arm_enum.LinkStatus.SUSPENDED)

    assert arm_enum.should_redirect(link) is False  # correct: == ACTIVE

    # SILENT SITE: the else-branch was written when INACTIVE was the only
    # non-active state, and it absorbed the new one without a word.
    assert arm_enum.public_message(link) != SUSPENDED_MESSAGE

    # Accidentally correct -- the site was written as != INACTIVE, so it happens
    # to bill. Nothing forced this decision; the opposite spelling
    # (== ACTIVE) would have been equally idiomatic and silently wrong.
    assert arm_enum.counts_toward_quota(link) is True


def test_enum_arm_selects_behavior_at_every_call_site() -> None:
    # The defect is structural, not stylistic: adding a state means auditing
    # every comparison against the enum, and nothing marks them.
    source = (arm_enum.__file__)
    text = open(source).read()
    comparisons = text.count("link.status ==") + text.count("link.status !=")
    assert comparisons == 3, "each consumer re-decides the meaning of the state"


# --- Arm 3: value object ----------------------------------------------------

def test_vo_arm_has_zero_silent_sites() -> None:
    link = arm_vo.ShortLink("promo", "suspended")

    assert str(arm_vo.resolve(link)) == SUSPENDED_MESSAGE
    assert arm_vo.public_message(link) == SUSPENDED_MESSAGE
    assert int(arm_vo.quota_charge(link)) == 1


def test_vo_arm_consumers_were_never_touched_when_the_state_was_added() -> None:
    # The v1 consumers are correct for all three states because none of them
    # knows how many states there are.
    for status, message, weight in [
        ("active", "", 1),
        ("inactive", "This link is no longer available.", 0),
        ("suspended", SUSPENDED_MESSAGE, 1),
    ]:
        link = arm_vo.ShortLink("promo", status)
        assert arm_vo.public_message(link) == message
        assert int(arm_vo.quota_charge(link)) == weight


def test_vo_arm_rejects_a_state_with_no_behavior_row() -> None:
    # This is what replaces the enum audit: a state that nobody decided the
    # behavior for cannot be constructed at all.
    with pytest.raises(arm_vo.UnknownStatus):
        arm_vo.LinkStatus("archived")


def test_vo_arm_rejects_an_unknown_status_arriving_from_storage() -> None:
    # Same door, inbound (serialization.md rule 2): a stale persisted value
    # surfaces as a construction error on read rather than a wrong branch.
    with pytest.raises(arm_vo.UnknownStatus):
        arm_vo.ShortLink("promo", "deleted")


def test_vo_arm_resolution_is_a_value_not_a_selector() -> None:
    # Two resolutions of the same state are equal -- value semantics. No
    # consumer can switch on it, because it exposes nothing to switch on.
    a = arm_vo.ShortLink("x", "suspended").resolve()
    b = arm_vo.ShortLink("y", "suspended").resolve()
    assert a == b
    assert not [n for n in dir(a) if n.startswith("is_") or n.startswith("serve")]


if __name__ == "__main__":
    # Standalone runner: this spike must be runnable without pytest installed.
    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{failures} failure(s)")
    raise SystemExit(1 if failures else 0)
