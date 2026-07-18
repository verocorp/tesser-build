"""linkpolicy — our OWN destination-policy bounded context.

Decides whether a destination URL is allowed (scheme allow-list, host block-list,
org rules) and records each verdict. It is a *peer context we own*, reached by an
ordinary cross-context port — NOT a third-party safe-browsing feed (that would be
a vendor ACL, a different shape). It imports nothing from ``campaign``.

The package top level is the public seam: the ``Client`` Protocol and its
primitive-leaved DTOs, and nothing else.
"""

from linkpolicy.client import (
    CheckRequest,
    CheckResponse,
    Client,
    VerdictView,
)

__all__ = [
    "Client",
    "CheckRequest",
    "CheckResponse",
    "VerdictView",
]
