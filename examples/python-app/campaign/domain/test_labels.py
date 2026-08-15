from __future__ import annotations

import pytest

import campaign.domain.labels as labels
from tesser.errors import DomainError


def test_labels_equality_is_order_independent() -> None:
    a = labels.Labels((("env", "prod"), ("team", "growth")))
    b = labels.Labels((("team", "growth"), ("env", "prod")))
    assert a == b
    assert hash(a) == hash(b)


def test_labels_get_returns_a_value_object() -> None:
    tags = labels.Labels((("env", "prod"),))
    value = tags.get("env")
    assert value == labels.LabelValue("prod")
    assert tags.get("missing") is None


def test_labels_reject_empty_keys_and_values() -> None:
    with pytest.raises(DomainError):
        labels.Labels((("", "prod"),))
    with pytest.raises(DomainError):
        labels.Labels((("env", ""),))
    with pytest.raises(DomainError):
        labels.LabelValue("")


def test_labels_reject_a_duplicate_key() -> None:
    with pytest.raises(DomainError):
        labels.Labels((("env", "prod"), ("env", "dev")))


def test_labels_length_counts_entries() -> None:
    assert len(labels.Labels((("a", "1"), ("b", "2")))) == 2


def test_label_value_round_trips_through_its_canonical_exit() -> None:
    value = labels.LabelValue("prod")
    assert labels.LabelValue(str(value)) == value
