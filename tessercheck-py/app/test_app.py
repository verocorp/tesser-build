from __future__ import annotations

import app.app as app
import app.config as config
import tessercheck.component as component


def test_an_app_builds_one_component_per_slice() -> None:
    cfg = config.AppConfig(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )

    assert app.TessercheckApp(cfg).tessercheck.client is not None


def test_an_app_closes_its_components() -> None:
    cfg = config.AppConfig(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )
    built = app.TessercheckApp(cfg)

    built.close()

    assert built.tessercheck.client is not None
