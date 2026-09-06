from __future__ import annotations

import kernel


class TestIdentity:

    def test_an_identity_equals_by_value(self) -> None:
        first = kernel.Identity("a")
        second = kernel.Identity("a")
        assert first == second
