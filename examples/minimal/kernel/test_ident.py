from __future__ import annotations

import pytest

import kernel.ident as ident
import tesser.errors as errors


def test_an_ident_is_never_empty() -> None:
    with pytest.raises(errors.DomainError):
        ident.Ident("")


def test_an_ident_equals_by_value() -> None:
    assert ident.Ident("a") == ident.Ident("a")
    assert str(ident.Ident("a")) == "a"
