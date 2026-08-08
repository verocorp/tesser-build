"""The bool contender: state as a bool. What examples/python-app/campaign/domain/short_link.py:34 does today.

Each contender models the same thing -- a short link that is servable or not -- and
exposes the same three consumers. The test then adds a THIRD state (suspended
for billing) and counts silent sites: call sites that still run, still pass
their old tests, and are now wrong.
"""

from __future__ import annotations

import tesser.domain as ts


class ShortLink(ts.Entity):

    def __init__(self, slug: str, active: bool = True, suspended: bool = False) -> None:
        self._slug = slug
        self._active = active
        # The third state has to arrive as a SECOND flag: bool cannot carry it.
        # This is what makes (active=True, suspended=True) representable.
        self._suspended = suspended

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def active(self) -> bool:
        return self._active

    @property
    def suspended(self) -> bool:
        return self._suspended


# --- consumers, written against the two-state world and never revisited ---

def should_redirect(link: ShortLink) -> bool:
    return link.active


def public_message(link: ShortLink) -> str:
    return "" if link.active else "This link is no longer available."


def counts_toward_quota(link: ShortLink) -> bool:
    return link.active
