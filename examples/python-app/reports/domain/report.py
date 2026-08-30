from __future__ import annotations

import typing

import tesser.domain as ts

import reports.domain.values as values
import kernel.slug as kernel_slug


class LinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class Link(ts.ValueObject):

    def __init__(self, spec: LinkSpec) -> None:
        object.__setattr__(self, "_slug", kernel_slug.Slug(spec.slug))
        object.__setattr__(self, "_target_url", values.TargetURL(spec.target_url))

    @property
    def slug(self) -> kernel_slug.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    _slug: kernel_slug.Slug
    _target_url: values.TargetURL


class RecordedVerdictSpec(ts.Spec):

    def __init__(self, target_url: str, decision: str, reason: str) -> None:
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class RecordedVerdict(ts.ValueObject):

    def __init__(self, spec: RecordedVerdictSpec) -> None:
        object.__setattr__(self, "_target_url", values.TargetURL(spec.target_url))
        object.__setattr__(self, "_decision", values.Decision(spec.decision))
        object.__setattr__(self, "_reason", values.Reason(spec.reason))

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def decision(self) -> values.Decision:
        return self._decision

    @property
    def reason(self) -> values.Reason:
        return self._reason

    _target_url: values.TargetURL
    _decision: values.Decision
    _reason: values.Reason


class LinkVerdictSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, decision: str, reason: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class LinkVerdict(ts.ValueObject):

    def __init__(self, spec: LinkVerdictSpec) -> None:
        object.__setattr__(self, "_slug", kernel_slug.Slug(spec.slug))
        object.__setattr__(self, "_target_url", values.TargetURL(spec.target_url))
        object.__setattr__(self, "_decision", values.Decision(spec.decision))
        object.__setattr__(self, "_reason", values.Reason(spec.reason))

    @property
    def slug(self) -> kernel_slug.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def decision(self) -> values.Decision:
        return self._decision

    @property
    def reason(self) -> values.Reason:
        return self._reason

    _slug: kernel_slug.Slug
    _target_url: values.TargetURL
    _decision: values.Decision
    _reason: values.Reason


_ALLOWED: typing.Final[values.Decision] = values.Decision("allowed")
_UNRECORDED_DECISION: typing.Final[values.Decision] = values.Decision("allowed")
_UNRECORDED_REASON: typing.Final[values.Reason] = values.Reason("no verdict recorded")


class LinkVerdictsSpec(ts.Spec):

    def __init__(
        self, links: tuple[LinkSpec, ...], verdicts: tuple[RecordedVerdictSpec, ...]
    ) -> None:
        self.links = links
        self.verdicts = verdicts


class LinkVerdicts(ts.ValueObject):

    def __init__(self, spec: LinkVerdictsSpec) -> None:
        recorded: dict[values.TargetURL, RecordedVerdict] = {}
        for verdict_spec in spec.verdicts:
            verdict = RecordedVerdict(verdict_spec)
            recorded[verdict.target_url] = verdict
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
        rows.sort(key=lambda row: (row.decision == _ALLOWED, str(row.slug)))
        object.__setattr__(self, "_rows", tuple(rows))

    @property
    def rows(self) -> tuple[LinkVerdict, ...]:
        return self._rows

    _rows: tuple[LinkVerdict, ...]
