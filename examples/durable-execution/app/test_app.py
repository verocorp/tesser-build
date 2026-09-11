from __future__ import annotations

import tesser.testing as ts

import app as app
import ordering.component as ordering_component


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def get(self) -> app.AppConfig:
        spec = app.Spec(ordering_component.Config(ordering_component.Spec("http://localhost:8080")))
        return app.AppConfig(spec)


class TestAppConfig:

    def test_a_config_carries_the_component_config(self) -> None:
        spec = app.Spec(ordering_component.Config(ordering_component.Spec("http://localhost:8080")))
        app_config = app.AppConfig(spec)
        assert app_config.ordering is spec.ordering


class TestEnvConfigRepository:

    def test_the_environment_the_runner_supplied_is_read_into_a_config(self) -> None:
        app_config = app.EnvConfigRepository().get()
        assert isinstance(app_config, app.AppConfig)
        assert app_config.ordering.ingress == "http://localhost:8080"

    def test_each_read_returns_its_own_config(self) -> None:
        env_config_repository = app.EnvConfigRepository()
        assert env_config_repository.get() is not env_config_repository.get()


class TestDurableExecutionApp:

    def test_the_app_wires_ordering(self) -> None:
        spec = app.Spec(ordering_component.Config(ordering_component.Spec("http://localhost:8080")))
        durable_execution_app = app.DurableExecutionApp(app.AppConfig(spec))
        try:
            declared = [
                durable_execution_app.ordering.restate_order_runtime.order_actions_service.name,
                durable_execution_app.ordering.restate_order_runtime.order_orchestrator_workflow.name,
            ]
        finally:
            durable_execution_app.close()
        assert declared == ["OrderActions", "OrderOrchestrator"]


class TestAppLoader:

    def test_the_loader_builds_an_app_from_its_repository(self) -> None:
        durable_execution_app = app.AppLoader(FakeConfigRepository()).load()
        try:
            declared = [
                sorted(durable_execution_app.ordering.restate_order_runtime.order_actions_service.handlers),
                sorted(durable_execution_app.ordering.restate_order_runtime.order_orchestrator_workflow.handlers),
            ]
        finally:
            durable_execution_app.close()
        assert declared == [["price_product"], ["run"]]
