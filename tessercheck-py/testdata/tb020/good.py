#!/usr/bin/env python3
def double(x: int) -> int:
    return x * 2  # noqa: T201


def shout(text: str) -> str:  # type: ignore[misc]
    return text.upper()  # pragma: no cover
