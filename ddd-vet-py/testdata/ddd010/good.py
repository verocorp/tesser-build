"""A value object that hides its representation — DDD010 clean.

Classified as a value object (frozen dataclass with a method), it wraps a
primitive behind an underscore-private field; the only surface is ``__str__``.
A spec (public primitive fields, no method) is a *different* stereotype and is
correctly exempt — that contrast is the whole point of the discriminator.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    _value: str  # hidden — the primitive does not leak

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class SlugSpec:  # a spec exposes primitives on purpose — not a VO, not flagged
    value: str
