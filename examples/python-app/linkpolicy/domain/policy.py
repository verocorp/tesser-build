from __future__ import annotations

import typing
import urllib.parse

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_DEFAULT_SCHEMES: typing.Final[tuple[str, ...]] = ("https",)
_DEFAULT_BLOCKED: typing.Final[tuple[str, ...]] = ("evil.example", "malware.test")


class Scheme(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value.isalpha():
            raise errors.invalid("invalid_scheme", f"scheme {value!r} must be alphabetic")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Host(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("invalid_host", "host must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("invalid_target_url", "target url must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Reason(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("invalid_reason", "reason must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Decision(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in ("allowed", "denied"):
            raise errors.invalid("invalid_decision", f"decision {value!r} must be allowed or denied")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class VerdictSpec(ts.Spec):

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        self.target_url = target_url
        self.allowed = allowed
        self.reason = reason


class Verdict(ts.ValueObject):

    def __init__(self, spec: VerdictSpec) -> None:
        object.__setattr__(self, "_target_url", TargetURL(spec.target_url))
        object.__setattr__(self, "_allowed", Decision("allowed" if spec.allowed else "denied"))
        object.__setattr__(self, "_reason", Reason(spec.reason))

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


class PolicySpec(ts.Spec):

    def __init__(
        self,
        allowed_schemes: tuple[str, ...] = _DEFAULT_SCHEMES,
        blocked_hosts: tuple[str, ...] = _DEFAULT_BLOCKED,
    ) -> None:
        self.allowed_schemes = allowed_schemes
        self.blocked_hosts = blocked_hosts


class Policy(ts.ValueObject):

    def __init__(self, spec: PolicySpec) -> None:
        object.__setattr__(
            self, "_allowed_schemes", tuple(Scheme(s) for s in spec.allowed_schemes)
        )
        object.__setattr__(
            self, "_blocked_hosts", tuple(Host(h) for h in spec.blocked_hosts)
        )

    @property
    def allowed_schemes(self) -> tuple[Scheme, ...]:
        return self._allowed_schemes

    @property
    def blocked_hosts(self) -> tuple[Host, ...]:
        return self._blocked_hosts

    def evaluate(self, target_url: str) -> Verdict:
        parsed = urllib.parse.urlparse(target_url)
        if parsed.scheme not in {str(s) for s in self._allowed_schemes}:
            return Verdict(
                VerdictSpec(
                    target_url, False, f"scheme {parsed.scheme or '(none)'!r} not allowed"
                )
            )
        host = parsed.hostname or ""
        if host in {str(h) for h in self._blocked_hosts}:
            return Verdict(VerdictSpec(target_url, False, f"host {host!r} is blocked"))
        return Verdict(VerdictSpec(target_url, True, "ok"))

    _allowed_schemes: tuple[Scheme, ...]
    _blocked_hosts: tuple[Host, ...]
