from __future__ import annotations

import calls.component as component
import pgdatabase.database as pgdatabase_database


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        spec = component.Spec(storage="postgres://a@b/c", ingress="http://localhost:8080")

        config = component.Config(spec)

        assert config.database == pgdatabase_database.DatabaseRequest(spec.storage)

    def test_a_config_carries_the_engine_ingress(self) -> None:
        spec = component.Spec(storage="postgres://a@b/c", ingress="http://localhost:8080")

        config = component.Config(spec)

        assert config.ingress == spec.ingress


class TestCalls:

    async def test_the_component_publishes_the_restate_runtime_it_wired(self) -> None:
        config = component.Config(
            component.Spec(storage="postgres://nobody@nowhere/none", ingress="http://localhost:8080")
        )

        calls = component.Calls(config, pgdatabase_database.Database(config.database))
        registered = {
            calls.restate_call_runtime.call_actions_service.name: sorted(calls.restate_call_runtime.call_actions_service.handlers),
            calls.restate_call_runtime.call_orchestrator_workflow.name: sorted(
                calls.restate_call_runtime.call_orchestrator_workflow.handlers
            ),
        }
        await calls.close()

        assert registered == {"CallActions": ["record_call"], "CallOrchestrator": ["conduct_call"]}
