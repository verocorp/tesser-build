"""The ``ShortLink`` entity — the campaign context's aggregate root. Identity is
its ``Slug``; it carries a validated ``TargetURL`` and an active flag, and it is
the unit the repository persists.
"""

from __future__ import annotations

from campaign.domain.values import Slug, TargetURL


class ShortLink:
    def __init__(self, slug: Slug, target: TargetURL, *, active: bool = True) -> None:
        self._slug = slug
        self._target = target
        self._active = active

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
        self._active = False
