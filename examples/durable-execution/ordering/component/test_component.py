from __future__ import annotations

import ordering.component as component


class TestOrdering:

    def test_the_component_publishes_the_restate_definitions_it_wired(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://localhost:8080")))
        try:
            declared = {d.name: sorted(d.handlers) for job in ordering.jobs for d in job.definitions()}
        finally:
            ordering.close()
        assert declared == {"OrderingActions": ["quote"], "Ordering": ["run"]}


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(ingress="http://localhost:8080")
        config = component.Config(spec)
        assert config.ingress == spec.ingress
