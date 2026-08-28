from __future__ import annotations

import kernel.identity as identity


class TestIdentity:

    def test_an_identity_equals_by_value(self) -> None:
        first = identity.Identity("a")
        second = identity.Identity("a")
        assert first == second
