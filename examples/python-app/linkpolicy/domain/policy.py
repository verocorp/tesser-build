from __future__ import annotations

from urllib.parse import urlparse

import tesser.domain as ts


class Verdict(ts.ValueObject):

    target_url: str
    allowed: bool
    reason: str

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "target_url", target_url)
        object.__setattr__(self, "allowed", allowed)
        object.__setattr__(self, "reason", reason)


class Policy(ts.ValueObject):

    allowed_schemes: tuple[str, ...]
    blocked_hosts: tuple[str, ...]

    def __init__(self, allowed_schemes: tuple[str, ...], blocked_hosts: tuple[str, ...]) -> None:
        object.__setattr__(self, "allowed_schemes", allowed_schemes)
        object.__setattr__(self, "blocked_hosts", blocked_hosts)

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
