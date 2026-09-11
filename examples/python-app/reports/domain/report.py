from __future__ import annotations

import re
import typing

import tesser.domain as ts

import reports.domain.kernel as kernel
import tesser.errors as errors
import tesser.serialization as serialization

_URL_RE: typing.Final[re.Pattern[str]] = re.compile(r"https?://\S+")


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _URL_RE.fullmatch(value):
            raise errors.invalid("invalid_target_url", f"target url {value!r} must be http(s)")
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


class Reason(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("invalid_reason", "reason must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class LinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class Link(ts.ValueObject):

    def __init__(self, spec: LinkSpec) -> None:
        object.__setattr__(self, "_slug", kernel.Slug(spec.slug))
        object.__setattr__(self, "_target_url", TargetURL(spec.target_url))

    @property
    def slug(self) -> kernel.Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    _slug: kernel.Slug
    _target_url: TargetURL


class RecordedVerdictSpec(ts.Spec):

    def __init__(self, target_url: str, decision: str, reason: str) -> None:
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class RecordedVerdict(ts.ValueObject):

    def __init__(self, spec: RecordedVerdictSpec) -> None:
        object.__setattr__(self, "_target_url", TargetURL(spec.target_url))
        object.__setattr__(self, "_decision", Decision(spec.decision))
        object.__setattr__(self, "_reason", Reason(spec.reason))

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def decision(self) -> Decision:
        return self._decision

    @property
    def reason(self) -> Reason:
        return self._reason

    _target_url: TargetURL
    _decision: Decision
    _reason: Reason


class LinkVerdictSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, decision: str, reason: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class LinkVerdict(ts.ValueObject):

    def __init__(self, spec: LinkVerdictSpec) -> None:
        object.__setattr__(self, "_slug", kernel.Slug(spec.slug))
        object.__setattr__(self, "_target_url", TargetURL(spec.target_url))
        object.__setattr__(self, "_decision", Decision(spec.decision))
        object.__setattr__(self, "_reason", Reason(spec.reason))

    @property
    def slug(self) -> kernel.Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def decision(self) -> Decision:
        return self._decision

    @property
    def reason(self) -> Reason:
        return self._reason

    def _rank(self) -> tuple[bool, str]:
        return (self._decision == _ALLOWED, str(self._slug))

    _slug: kernel.Slug
    _target_url: TargetURL
    _decision: Decision
    _reason: Reason


_ALLOWED: typing.Final[Decision] = Decision("allowed")
_UNRECORDED_DECISION: typing.Final[Decision] = Decision("allowed")
_UNRECORDED_REASON: typing.Final[Reason] = Reason("no verdict recorded")


class LinkVerdictsSpec(ts.Spec):

    def __init__(
        self, links: tuple[LinkSpec, ...], verdicts: tuple[RecordedVerdictSpec, ...]
    ) -> None:
        self.links = links
        self.verdicts = verdicts


class LinkVerdicts(ts.ValueObject):

    def __init__(self, spec: LinkVerdictsSpec) -> None:
        recorded: dict[TargetURL, RecordedVerdict] = {}
        for verdict_spec in spec.verdicts:
            recorded_verdict = RecordedVerdict(verdict_spec)
            recorded[recorded_verdict.target_url] = recorded_verdict
        rows: list[LinkVerdict] = []
        for link_spec in spec.links:
            link = Link(link_spec)
            ruled = recorded.get(link.target_url)
            decision = _UNRECORDED_DECISION if ruled is None else ruled.decision
            reason = _UNRECORDED_REASON if ruled is None else ruled.reason
            rows.append(
                LinkVerdict(
                    LinkVerdictSpec(
                        slug=str(link.slug),
                        target_url=str(link.target_url),
                        decision=str(decision),
                        reason=str(reason),
                    )
                )
            )
        rows.sort(key=LinkVerdict._rank)
        object.__setattr__(self, "_rows", tuple(rows))

    @property
    def rows(self) -> tuple[LinkVerdict, ...]:
        return self._rows

    _rows: tuple[LinkVerdict, ...]
