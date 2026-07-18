"""The linkpolicy domain: the ``Policy`` value object that decides whether a
destination URL is allowed, and the ``Verdict`` it produces.

The policy is intrinsic behavior, not wiring — exactly the kind of scheme/host
rule that belongs in a model, not scattered across callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Verdict:
    """The outcome of evaluating one destination URL against the policy."""

    target_url: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class Policy:
    """Allowed URL schemes + blocked hosts. A value object: equal by value,
    constructed once, no representation leak."""

    allowed_schemes: tuple[str, ...]
    blocked_hosts: tuple[str, ...]

    @staticmethod
    def default() -> Policy:
        return Policy(allowed_schemes=("https",), blocked_hosts=("evil.example", "malware.test"))

    def evaluate(self, target_url: str) -> Verdict:
        parsed = urlparse(target_url)
        if parsed.scheme not in self.allowed_schemes:
            return Verdict(target_url, False, f"scheme {parsed.scheme or '(none)'!r} not allowed")
        host = parsed.hostname or ""
        if host in self.blocked_hosts:
            return Verdict(target_url, False, f"host {host!r} is blocked")
        return Verdict(target_url, True, "ok")
