"""The enum contender: state as an enum -- a closed set of named constants that SELECTS behavior.

This is the shape value-objects.md:29-30 calls "a primitive with a name," and
the shape the maintainer ruling keeps primitive. It exists to measure what
that ruling costs and buys, not to advocate for it.
"""

from __future__ import annotations

from enum import Enum

import tesser.domain as ts


class LinkStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"  # added in v2


class ShortLink(ts.Entity):

    def __init__(self, slug: str, status: LinkStatus = LinkStatus.ACTIVE) -> None:
        self._slug = slug
        self._status = status

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def status(self) -> LinkStatus:
        return self._status


# --- consumers: behavior is SELECTED at each call site, which is the defect ---

def should_redirect(link: ShortLink) -> bool:
    return link.status == LinkStatus.ACTIVE


def public_message(link: ShortLink) -> str:
    # Written when INACTIVE was the only non-active state. Still runs.
    return "" if link.status == LinkStatus.ACTIVE else "This link is no longer available."


def counts_toward_quota(link: ShortLink) -> bool:
    # The inverted form: everything-not-inactive bills. Suspended now bills.
    return link.status != LinkStatus.INACTIVE
