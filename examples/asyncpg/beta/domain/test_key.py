from __future__ import annotations

import beta.domain as domain


class TestKey:

    def test_a_key_equals_by_value(self) -> None:
        first = domain.Key("k")
        second = domain.Key("k")
        assert first == second
