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
    lifecycle (active -> deactivated). Its identity is its Slug — two short
    links with the same slug in the same campaign would be the same link, and
    the rule forbidding duplicate slugs within a campaign is exactly the
    identity rule an entity earns.

    Fields are value objects, never raw primitives; underscore-private with
    read-only ``@property`` accessors and no setters. Equality is identity (by
    slug), so ``__eq__`` and ``__hash__`` are defined together.
    """

    def __init__(self, slug: Slug, target_url: TargetURL, active: bool) -> None:
        self._slug = slug
        self._target_url = target_url
        self._active = active

    @classmethod
    def from_spec(cls, spec: ShortLinkSpec) -> "ShortLink":
        """Build each child value object via its own constructor, adding error
        context; re-validate nothing."""
        try:
            slug = Slug(spec.slug)
        except ValueError as e:
            raise ValueError(f"invalid slug: {e}") from e
        try:
            target_url = TargetURL(spec.target_url)
        except ValueError as e:
            raise ValueError(f"invalid target url: {e}") from e
        return cls(slug, target_url, spec.active)

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

    def __eq__(self, other: object) -> bool:
        # Identity, not attributes: two short links are the same iff same slug.
        return isinstance(other, ShortLink) and other._slug == self._slug

    def __hash__(self) -> int:
        return hash(self._slug)
