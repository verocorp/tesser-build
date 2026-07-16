import copy
from dataclasses import dataclass

from campaign.slug import Slug
from campaign.target_url import TargetURL


@dataclass(frozen=True)
class ShortLinkSpec:
    """Carries construction data across the layer boundary: primitive leaves
    only. ``active`` is included (rather than assumed true) so a repository can
    reconstruct a previously-deactivated link through this same constructor;
    application-service creation paths always pass ``active=True``, since there
    is no use case for creating an already-deactivated link.
    """

    slug: str
    target_url: str
    active: bool


class ShortLink:
    """The entity a Campaign owns: a slug mapped to a target URL, with a
    lifecycle (active -> deactivated). It earns identity from that lifecycle —
    the system tracks *this specific link* as it changes state — and its Slug
    serves as its natural-key ID (equality is by slug). The Campaign separately
    enforces that no two of its short links share a slug; that uniqueness is an
    aggregate invariant, not the source of the entity's identity (see
    entities.md — a uniqueness constraint is not identity).

    Fields are value objects, never raw primitives; underscore-private with
    read-only ``@property`` accessors and no setters. Equality is identity (by
    slug), so ``__eq__`` and ``__hash__`` are defined together.
    """

    def __init__(self, spec: ShortLinkSpec) -> None:
        """Construct from the spec — the single construction path. Each child
        value object validates itself; the constructor only adds error context.
        """
        try:
            self._slug = Slug(spec.slug)
        except ValueError as e:
            raise ValueError(f"invalid slug: {e}") from e
        try:
            self._target_url = TargetURL(spec.target_url)
        except ValueError as e:
            raise ValueError(f"invalid target url: {e}") from e
        self._active = spec.active

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        """The entity's guarded lifecycle transition: two states -> one guard
        clause. A short link can only be deactivated once."""
        if not self._active:
            raise ValueError(f"short link {self._slug} is already deactivated")
        self._active = False

    def _clone(self) -> "ShortLink":
        """An independent copy the aggregate hands out from its accessor.
        ShortLink is mutable, so returning the real object would let a caller
        deactivate it directly and bypass the root; a caller may only mutate a
        copy. slug and target_url are immutable value objects, so a shallow copy
        is genuinely independent — and it sidesteps re-validating already-valid
        children through the spec constructor."""
        return copy.copy(self)

    def __eq__(self, other: object) -> bool:
        # Identity, not attributes: two short links are the same iff same slug.
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
