from __future__ import annotations

import ordering.component.component as component
import ordering.component.config as config


class TestOrdering:

    def test_the_component_publishes_the_restate_definitions_it_wired(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        try:
            declared = {d.name: sorted(d.handlers) for job in wired.jobs for d in job.definitions()}
        finally:
            wired.close()
        assert declared == {"OrderingActions": ["quote"], "Ordering": ["run"]}
