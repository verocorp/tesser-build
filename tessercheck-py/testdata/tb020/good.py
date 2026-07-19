#!/usr/bin/env python3
# -*- coding: utf-8 -*-
def double(x: int) -> int:
    return x * 2  # noqa: T201


def shout(text: str) -> str:  # type: ignore[misc]
    return text.upper()  # pragma: no cover


def fmt_controlled(x: int) -> int:
    # fmt: off
    y = (x +
         1)
    # fmt: on
    return y  # isort:skip


def ruff_controlled(x: int) -> int:
    # ruff: noqa
    return x  # tessercheck:ignore


# tb-cell: value-objects py-example ✅
# tb-status: full
# tb-allow-missing: examples/app
def marked(x: int) -> int:
    return x
