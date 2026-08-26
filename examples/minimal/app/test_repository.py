from __future__ import annotations

import os

import pytest

import app.repository as repository
import tesser.errors as errors


def test_the_environment_is_read_into_a_config() -> None:
    os.environ["ALPHA_STORAGE"] = "memory"
    os.environ["BETA_KEYS"] = "w,x"
    cfg = repository.EnvConfigRepository().get()
    assert cfg.alpha.storage == "memory"
    assert cfg.beta.keys == ("w", "x")


def test_a_missing_variable_is_a_validation_error() -> None:
    os.environ.pop("ALPHA_STORAGE", None)
    with pytest.raises(errors.DomainError):
        repository.EnvConfigRepository().get()
