from __future__ import annotations

import pytest

import beta.domain.key as key
import tesser.errors as errors


def test_a_key_is_never_empty() -> None:
    with pytest.raises(errors.DomainError):
        key.Key("")
    assert key.Key("k") == key.Key("k")
