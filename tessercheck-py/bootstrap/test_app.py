from __future__ import annotations

import bootstrap.app as app
import bootstrap.config as config
import tessercheck.wiring.config as component_config


def test_an_app_builds_one_component_per_slice() -> None:
    cfg = config.Config(
        config.Spec(tessercheck=component_config.Config(component_config.Spec()))
    )

    assert app.App(cfg).tessercheck.client is not None


def test_an_app_closes_its_components() -> None:
    cfg = config.Config(
        config.Spec(tessercheck=component_config.Config(component_config.Spec()))
    )
    built = app.App(cfg)

    built.close()

    assert built.tessercheck.client is not None
