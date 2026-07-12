"""The public contract for the link-campaign component — the entire surface
other code (an HTTP layer, another module) is meant to depend on. It declares
the ``Client`` Protocol and its DTOs only; no behavior, no domain types cross
this boundary.

The ``Client`` is a *decoupling boundary*: callers depend on this package and
never on the application-service, repository, or domain packages behind it, so
those internals can be refactored, renamed, or recomposed freely as long as
this contract holds. In Python the boundary is a ``Protocol``, satisfied
structurally — the concrete application service satisfies ``Client`` without
inheriting from it (see ``linkcampaignimpl``).

DTOs are frozen dataclasses with primitive leaves. Unlike the Go rendering,
the methods carry no ``context.Context`` — a plain synchronous Python service
has no such idiom; thread a unit-of-work/session in the way your codebase
already does if you need one.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ShortLinkInput:
    """The primitive-leaved shape of a short link supplied when creating a
    campaign."""

    slug: str
    target_url: str


@dataclass(frozen=True)
class ShortLinkView:
    """The primitive-leaved shape of a short link returned to a caller — never
    a domain object."""

    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class CreateCampaignRequest:
    name: str
    links: tuple[ShortLinkInput, ...]


@dataclass(frozen=True)
class CreateCampaignResponse:
    campaign_id: str
    name: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class AddShortLinkRequest:
    campaign_id: str
    slug: str
    target_url: str


@dataclass(frozen=True)
class AddShortLinkResponse:
    campaign_id: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class DeactivateShortLinkRequest:
    campaign_id: str
    slug: str


@dataclass(frozen=True)
class DeactivateShortLinkResponse:
    campaign_id: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class GetCampaignRequest:
    campaign_id: str


@dataclass(frozen=True)
class GetCampaignResponse:
    campaign_id: str
    name: str
    links: tuple[ShortLinkView, ...]


class Client(Protocol):
    """The entire public surface of the link-campaign component."""

    def create_campaign(self, req: CreateCampaignRequest) -> CreateCampaignResponse: ...

    def add_short_link(self, req: AddShortLinkRequest) -> AddShortLinkResponse: ...

    def deactivate_short_link(
        self, req: DeactivateShortLinkRequest
    ) -> DeactivateShortLinkResponse: ...

    def get_campaign(self, req: GetCampaignRequest) -> GetCampaignResponse: ...
