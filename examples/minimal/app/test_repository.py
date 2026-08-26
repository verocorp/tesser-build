from __future__ import annotations

import os

import app.repository as repository


def test_the_environment_is_read_into_a_config() -> None:
    os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="k")
    assert repository.EnvConfigRepository().get().beta.key == "k"
