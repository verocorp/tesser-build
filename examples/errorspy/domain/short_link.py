"""ShortLink: an entity, identified by its slug, with mutable active-state.

Construction (cell C3) builds its child VOs and lets a child DomainError
propagate UNCHANGED — the child already carries full identity (kind, code,
field), so re-wrapping it (Go's reflexive ``%w``) would only add noise. We wrap
only when we add context a child cannot know; that happens at the aggregate
(collection index), not here.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.values import Slug, TargetURL
from errors import conflict


@dataclass(frozen=True)
class ShortLinkSpec:
    slug: str
    target_url: str


class ShortLink:
    """Entity: identity is the slug; ``active`` is mutable state."""

    def __init__(self, spec: ShortLinkSpec) -> None:
        # C3: child VOs validate; a child DomainError propagates as-is.
        self._slug = Slug(spec.slug)
        self._target = TargetURL(spec.target_url)
        self._active = True

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target(self) -> TargetURL:
        return self._target

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        # D1: an illegal transition is a conflict, not a validation error.
        if not self._active:
            raise conflict(
                "already_deactivated", f"short link {self._slug} is already deactivated"
            )
        self._active = False

    # Identity equality (by slug) — __eq__ and __hash__ defined together.
    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
