from __future__ import annotations

import app.app as app
import app.config as config
import ordering.component.config as ordering_config


class TestApp:

    def test_the_app_wires_ordering(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        built = app.App(config.Config(spec))
        try:
            declared = [d.name for job in built.ordering.jobs for d in job.definitions()]
        finally:
            built.close()
        assert declared == ["OrderingActions", "Ordering"]
