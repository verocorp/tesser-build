from __future__ import annotations

from typing import Final
from urllib.parse import urlparse  # tessercheck:ignore TB062

import tesser.domain as ts

from tesser.errors import invalid
from tesser.serialization import canonical_str

_DEFAULT_SCHEMES: Final[tuple[str, ...]] = ("https",)
_DEFAULT_BLOCKED: Final[tuple[str, ...]] = ("evil.example", "malware.test")


class Scheme(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value.isalpha():
            raise invalid("invalid_scheme", f"scheme {value!r} must be alphabetic")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Host(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise invalid("invalid_host", "host must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise invalid("invalid_target_url", "target url must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Reason(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise invalid("invalid_reason", "reason must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Decision(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in ("allowed", "denied"):
            raise invalid("invalid_decision", f"decision {value!r} must be allowed or denied")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Verdict(ts.ValueObject):

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "_target_url", TargetURL(target_url))
        object.__setattr__(self, "_allowed", Decision("allowed" if allowed else "denied"))
        object.__setattr__(self, "_reason", Reason(reason))

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def allowed(self) -> Decision:
        return self._allowed

    @property
    def reason(self) -> Reason:
        return self._reason

    _target_url: TargetURL
    _allowed: Decision
    _reason: Reason


class Policy(ts.ValueObject):

    def __init__(
        self,
        allowed_schemes: tuple[str, ...] = _DEFAULT_SCHEMES,
        blocked_hosts: tuple[str, ...] = _DEFAULT_BLOCKED,
    ) -> None:
        object.__setattr__(
            self, "_allowed_schemes", tuple(Scheme(s) for s in allowed_schemes)
        )
        object.__setattr__(
            self, "_blocked_hosts", tuple(Host(h) for h in blocked_hosts)
        )

    @property
    def allowed_schemes(self) -> tuple[Scheme, ...]:
        return self._allowed_schemes

    @property
    def blocked_hosts(self) -> tuple[Host, ...]:
        return self._blocked_hosts

    def evaluate(self, target_url: str) -> Verdict:
        parsed = urlparse(target_url)
        if parsed.scheme not in {str(s) for s in self._allowed_schemes}:
            return Verdict(
                target_url, False, f"scheme {parsed.scheme or '(none)'!r} not allowed"
            )
        host = parsed.hostname or ""
        if host in {str(h) for h in self._blocked_hosts}:
            return Verdict(target_url, False, f"host {host!r} is blocked")
        return Verdict(target_url, True, "ok")

    _allowed_schemes: tuple[Scheme, ...]
    _blocked_hosts: tuple[Host, ...]
