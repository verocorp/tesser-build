from __future__ import annotations

import beta.domain.key as key


class TestKey:

    def test_a_key_equals_by_value(self) -> None:
        first = key.Key("k")
        second = key.Key("k")
        assert first == second
