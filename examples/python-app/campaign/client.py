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

    allowed: bool
    reason: str


class TargetChecker(Protocol):

    def check(self, target_url: str) -> CheckOutcome: ...


class Client(Protocol):

    def create_link(self, req: CreateLinkRequest) -> CreateLinkResponse: ...

    def resolve(self, req: ResolveRequest) -> ResolveResponse: ...

    def list_links(self) -> tuple[LinkView, ...]: ...
