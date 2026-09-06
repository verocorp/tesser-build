from __future__ import annotations

import pytest

import campaign.domain as domain
import tesser.errors as errors


def test_labels_equality_is_order_independent() -> None:
    a = domain.Labels((("env", "prod"), ("team", "growth")))
    b = domain.Labels((("team", "growth"), ("env", "prod")))
    assert a == b
    assert hash(a) == hash(b)


def test_labels_get_returns_a_value_object() -> None:
    labels = domain.Labels((("env", "prod"),))
    value = labels.get("env")
    assert value == domain.LabelValue("prod")
    assert labels.get("missing") is None


def test_labels_reject_empty_keys_and_values() -> None:
    with pytest.raises(errors.DomainError):
        domain.Labels((("", "prod"),))
    with pytest.raises(errors.DomainError):
        domain.Labels((("env", ""),))
    with pytest.raises(errors.DomainError):
        domain.LabelValue("")


def test_labels_reject_a_duplicate_key() -> None:
    with pytest.raises(errors.DomainError):
        domain.Labels((("env", "prod"), ("env", "dev")))


def test_labels_length_counts_entries() -> None:
    assert len(domain.Labels((("a", "1"), ("b", "2")))) == 2


def test_label_value_round_trips_through_its_canonical_exit() -> None:
    label_value = domain.LabelValue("prod")
    assert domain.LabelValue(str(label_value)) == label_value
