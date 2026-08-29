from __future__ import annotations

import app.app as app
import app.config as config
import ordering.component.config as ordering_config


class TestApp:

    def test_the_app_wires_ordering(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        built = app.App(config.Config(spec))
        try:
            declared = [d.name for d in built.ordering.jobs.definitions()]
        finally:
            built.close()
        assert declared == ["Ordering", "OrderingActions"]
