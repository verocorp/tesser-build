from __future__ import annotations

import shared.label as label


class TestLabel:

    def test_a_label_equals_by_value(self) -> None:
        first = label.Label("x")
        second = label.Label("x")
        assert first == second
