"""campaign — the short-link bounded context: create + resolve (redirect).

Reuses the running example's short-link value-object idiom. The package top level
is the public seam: the ``Client`` Protocol, its primitive-leaved DTOs, and the
one OUTBOUND port campaign owns — ``TargetChecker`` — which it needs a peer
context to satisfy (Moment 1). Its own construction config lives in ``wiring``,
never here.
"""

from campaign.client import (
    CheckOutcome,
    Client,
    CreateLinkRequest,
    CreateLinkResponse,
    LinkView,
    ResolveRequest,
    ResolveResponse,
    TargetChecker,
)

__all__ = [
    "Client",
    "TargetChecker",
    "CheckOutcome",
    "CreateLinkRequest",
    "CreateLinkResponse",
    "ResolveRequest",
    "ResolveResponse",
    "LinkView",
]
