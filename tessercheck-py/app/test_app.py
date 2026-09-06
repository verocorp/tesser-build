from __future__ import annotations

import app.app as app
import app.config as config
import tessercheck.component as component


def test_an_app_builds_one_component_per_slice() -> None:
    app_config = config.AppConfig(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )

    assert app.TessercheckApp(app_config).tessercheck.client is not None


def test_an_app_closes_its_components() -> None:
    app_config = config.AppConfig(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )
    tessercheck_app = app.TessercheckApp(app_config)

    tessercheck_app.close()

    assert tessercheck_app.tessercheck.client is not None
