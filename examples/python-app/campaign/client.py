"""The public contract for the campaign context.

``Client`` + primitive-leaved DTOs, plus ``TargetChecker`` — the outbound port
campaign OWNS and a peer context must satisfy. Declaring the port here (beside the
Client) is what lets the composition root build an adapter for it and inject it;
campaign never imports the peer context's package itself (the adapter, in
``adapters/gateways``, does).

``CheckOutcome`` is campaign's OWN word for a verdict — the adapter translates the
peer context's DTO into it, so linkpolicy's vocabulary never crosses inward.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CreateLinkRequest:
    slug: str
    target_url: str


@dataclass(frozen=True)
class CreateLinkResponse:
    slug: str
    target_url: str


@dataclass(frozen=True)
class ResolveRequest:
    slug: str


@dataclass(frozen=True)
class ResolveResponse:
    target_url: str


@dataclass(frozen=True)
class LinkView:
    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class CheckOutcome:
    """campaign's own verdict shape — what ``TargetChecker`` returns."""

    allowed: bool
    reason: str


class TargetChecker(Protocol):
    """Outbound port: vet a destination URL before a link is minted.

    Coupled failure is *correct* here — if the checker rejects OR is unavailable,
    link creation MUST fail (fail-closed): you cannot mint a link to an un-vetted
    destination. An outage surfaces as an ``errors.InfraError`` that propagates.
    """

    def check(self, target_url: str) -> CheckOutcome: ...


class Client(Protocol):
    """The entire public surface of the campaign context."""

    def create_link(self, req: CreateLinkRequest) -> CreateLinkResponse: ...

    def resolve(self, req: ResolveRequest) -> ResolveResponse: ...

    def list_links(self) -> tuple[LinkView, ...]: ...
