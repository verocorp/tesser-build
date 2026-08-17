from __future__ import annotations

import app.app as app
import app.config as config
import repo.component.config as repo_config


def test_an_app_builds_one_component_per_slice() -> None:
    cfg = config.Config(config.Spec(repo=repo_config.Config(repo_config.Spec())))

    assert app.App(cfg).repo.client is not None


def test_an_app_closes_its_components() -> None:
    cfg = config.Config(config.Spec(repo=repo_config.Config(repo_config.Spec())))
    built = app.App(cfg)

    built.close()

    assert built.repo.client is not None
