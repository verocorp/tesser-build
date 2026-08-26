from __future__ import annotations

import kernel.ident as ident


def test_an_ident_equals_by_value() -> None:
    assert ident.Ident("a") == ident.Ident("a")
