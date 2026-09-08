from __future__ import annotations

import ordering.component as component


class TestOrdering:

    def test_the_component_publishes_the_restate_runtime_it_wired(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://localhost:8080")))
        try:
            declared = {
                ordering.restate_order_runtime.order_actions_service.name: sorted(
                    ordering.restate_order_runtime.order_actions_service.handlers
                ),
                ordering.restate_order_runtime.order_orchestrator_workflow.name: sorted(
                    ordering.restate_order_runtime.order_orchestrator_workflow.handlers
                ),
            }
        finally:
            ordering.close()
        assert declared == {"OrderActions": ["price_product"], "OrderOrchestrator": ["run"]}


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(ingress="http://localhost:8080")
        config = component.Config(spec)
        assert config.ingress == spec.ingress
