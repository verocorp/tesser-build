"""Arm 3: the only arm that actually satisfies the rule under test.

The rule ("no primitive returns, and an enum is a primitive") does not turn
`active -> bool` into `active -> SomeEnumLikeVO`. That would be arm 2 wearing a
value object's coat: the call site still asks "which one is it?" and selects
behavior itself.

What the rule actually forces is that **the predicate stops existing**. The
branch folds into the type: consumers no longer ask the link about its state,
they ask it for a Resolution, and the Resolution is a value object. The bool is
never produced, so it cannot leak -- and the call sites that used to select
behavior have nothing left to select.

The cost is visible below: three states now cost a registry row each, and the
domain owns the public message it previously left to the edge.
"""

from __future__ import annotations

from typing import Final

import tesser.domain as ts


class UnknownStatus(Exception):
    """Raised when a persisted or wire status has no behavior row."""


class Resolution(ts.ValueObject):
    """What the domain decided to do about a request for a link.

    A value object, not an enum: it carries the decision AND the data the
    decision needs, it is constructed by validation, and no consumer switches
    on it. Its canonical exit is the public message (serialization.md rule 3).
    """

    def __init__(self, serve: bool, message: str, billable: bool) -> None:
        # These primitives are constructor INPUT, never output. The rule under
        # test governs returns; a spec-shaped constructor is untouched by it.
        object.__setattr__(self, "_serve", serve)
        object.__setattr__(self, "_message", message)
        object.__setattr__(self, "_billable", billable)

    def __str__(self) -> str:
        return self._message

    _serve: bool
    _message: str
    _billable: bool


class QuotaWeight(ts.ValueObject):

    def __init__(self, units: int) -> None:
        if units < 0:
            raise ValueError(f"quota weight must not be negative: {units}")
        object.__setattr__(self, "_units", units)

    def __int__(self) -> int:
        return self._units

    _units: int


# The registry is the single site a new state is added, and every column is
# mandatory -- adding SUSPENDED without deciding whether it bills is a
# construction-time failure, not a silent default.
_BEHAVIOR: Final[dict[str, tuple[bool, str, int]]] = {
    "active": (True, "", 1),
    "inactive": (False, "This link is no longer available.", 0),
    "suspended": (False, "This link is temporarily suspended.", 1),  # added in v2
}


class LinkStatus(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in _BEHAVIOR:
            raise UnknownStatus(f"unknown link status {value!r}")
        object.__setattr__(self, "_value", value)

    def resolve(self) -> Resolution:
        serve, message, weight = _BEHAVIOR[self._value]
        return Resolution(serve=serve, message=message, billable=weight > 0)

    def quota_weight(self) -> QuotaWeight:
        return QuotaWeight(_BEHAVIOR[self._value][2])

    def __str__(self) -> str:
        return self._value

    _value: str


class ShortLink(ts.Entity):

    def __init__(self, slug: str, status: str = "active") -> None:
        self._slug = slug
        self._status = LinkStatus(status)

    @property
    def status(self) -> LinkStatus:
        return self._status

    def resolve(self) -> Resolution:
        return self._status.resolve()

    def quota_weight(self) -> QuotaWeight:
        return self._status.quota_weight()


# --- consumers: nothing to select. There is no predicate to get wrong. ---

def resolve(link: ShortLink) -> Resolution:
    return link.resolve()


def public_message(link: ShortLink) -> str:
    # The edge's canonical exit -- licensed, and the ONLY primitive here.
    return str(link.resolve())


def quota_charge(link: ShortLink) -> QuotaWeight:
    return link.quota_weight()
