from __future__ import annotations

import shared


class TestLabel:

    def test_a_label_equals_by_value(self) -> None:
        first = shared.Label("x")
        second = shared.Label("x")
        assert first == second
