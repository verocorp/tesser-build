from __future__ import annotations

import tesser.domain as ts

import reports.domain.values as values


class Link(ts.ValueObject):

    def __init__(self, slug: str, target_url: str) -> None:
        object.__setattr__(self, "_slug", values.Slug(slug))
        object.__setattr__(self, "_target_url", values.TargetURL(target_url))

    @property
    def slug(self) -> values.Slug:
        return self._slug

    @property
    def target_url(self) -> values.TargetURL:
        return self._target_url

    _slug: values.Slug
    _target_url: values.TargetURL


class RecordedVerdict(ts.ValueObject):

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "_target_url", values.TargetURL(target_url))
        object.__setattr__(self, "_allowed", values.Decision("allowed" if allowed else "denied"))
        object.__setattr__(self, "_reason", values.Reason(reason))

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


class LinkVerdict(ts.ValueObject):

    def __init__(self, slug: str, target_url: str, allowed: bool, reason: str) -> None:
        object.__setattr__(self, "_slug", values.Slug(slug))
        object.__setattr__(self, "_target_url", values.TargetURL(target_url))
        object.__setattr__(self, "_allowed", values.Decision("allowed" if allowed else "denied"))
        object.__setattr__(self, "_reason", values.Reason(reason))

    @property
    def slug(self) -> values.Slug:
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

    _slug: values.Slug
    _target_url: values.TargetURL
    _allowed: values.Decision
    _reason: values.Reason


@ts.do_not_use_function
def join_links_with_verdicts(
    links: tuple[Link, ...], verdicts: tuple[RecordedVerdict, ...]
) -> tuple[LinkVerdict, ...]:
    by_url = {str(v.target_url): v for v in verdicts}
    rows = [
        LinkVerdict(
            slug=str(link.slug),
            target_url=str(link.target_url),
            allowed=str(by_url[str(link.target_url)].allowed) == "allowed"
            if str(link.target_url) in by_url
            else True,
            reason=str(by_url[str(link.target_url)].reason)
            if str(link.target_url) in by_url
            else "no verdict recorded",
        )
        for link in links
    ]
    return tuple(sorted(rows, key=lambda r: (str(r.allowed) == "allowed", str(r.slug))))
