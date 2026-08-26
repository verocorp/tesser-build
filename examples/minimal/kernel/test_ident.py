from __future__ import annotations

import kernel.ident as ident


class TestIdent:

    def test_an_ident_equals_by_value(self) -> None:
        first = ident.Ident("a")
        second = ident.Ident("a")
        assert first == second
