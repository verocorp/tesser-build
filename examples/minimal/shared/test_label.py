from __future__ import annotations

import shared.label as label


def test_a_label_equals_by_value() -> None:
    assert label.Label("x") == label.Label("x")
