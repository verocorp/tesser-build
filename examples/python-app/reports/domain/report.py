from __future__ import annotations

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

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        self.target_url = target_url
        self.allowed = allowed
        self.reason = reason


class RecordedVerdict(ts.ValueObject):

    def __init__(self, spec: RecordedVerdictSpec) -> None:
        object.__setattr__(self, "_target_url", values.TargetURL(spec.target_url))
        object.__setattr__(self, "_allowed", values.Decision("allowed" if spec.allowed else "denied"))
        object.__setattr__(self, "_reason", values.Reason(spec.reason))

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def allowed(self) -> values.Decision:
        return self._allowed

    @property
    def reason(self) -> values.Reason:
        return self._reason

    _target_url: values.TargetURL
    _allowed: values.Decision
    _reason: values.Reason


class LinkVerdictSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, allowed: bool, reason: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.allowed = allowed
        self.reason = reason


class LinkVerdict(ts.ValueObject):

    def __init__(self, spec: LinkVerdictSpec) -> None:
        object.__setattr__(self, "_slug", kernel_slug.Slug(spec.slug))
        object.__setattr__(self, "_target_url", values.TargetURL(spec.target_url))
        object.__setattr__(self, "_allowed", values.Decision("allowed" if spec.allowed else "denied"))
        object.__setattr__(self, "_reason", values.Reason(spec.reason))

    @property
    def slug(self) -> kernel_slug.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    @property
    def allowed(self) -> values.Decision:
        return self._allowed

    @property
    def reason(self) -> values.Reason:
        return self._reason

    _slug: kernel_slug.Slug
    _target_url: values.TargetURL
    _allowed: values.Decision
    _reason: values.Reason
