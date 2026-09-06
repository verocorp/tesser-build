from __future__ import annotations

import pytest
import tesser.testing as ts

import app as app
import campaign.client as campaign_client
import campaign.component as campaign_component
import linkpolicy.component as linkpolicy_component
import reports.client as reports_client
import reports.component as reports_component
import tesser.errors as errors


@ts.helper
def _app_spec(
    campaign_storage: str = "memory",
    linkpolicy_storage: str = "memory",
    host: str = "",
    port: int = 8080,
) -> app.Spec:
    return app.Spec(
        campaign=campaign_component.Config(campaign_component.Spec(storage=campaign_storage)),
        linkpolicy=linkpolicy_component.Config(
            linkpolicy_component.Spec(storage=linkpolicy_storage)
        ),
        reports=reports_component.Config(reports_component.Spec()),
        http=app.HttpConfig(app.HttpSpec(host, port)),
    )


@ts.fake
class FakeConfigRepository(app.AppConfigRepository):

    def __init__(self) -> None:
        self.reads = 0

    def get(self) -> app.AppConfig:
        self.reads += 1
        return app.AppConfig(_app_spec())


def test_a_config_carries_one_slice_per_component() -> None:
    app_config = app.AppConfig(_app_spec(linkpolicy_storage="postgres"))

    assert app_config.campaign.storage == "memory"
    assert app_config.linkpolicy.storage == "postgres"


def test_an_http_config_carries_the_coordinate_it_was_given() -> None:
    http_config = app.HttpConfig(app.HttpSpec("127.0.0.1", 9091))

    assert http_config.host == "127.0.0.1"
    assert http_config.port == 9091


def test_an_app_builds_one_component_per_slice() -> None:
    python_app = app.PythonApp(app.AppConfig(_app_spec()))

    assert python_app.campaign.client is not None
    assert python_app.linkpolicy.client is not None
    assert python_app.reports.client is not None


def test_an_app_wires_its_components_to_each_other() -> None:
    python_app = app.PythonApp(app.AppConfig(_app_spec()))

    campaign_view = python_app.campaign.client.create_campaign(
        campaign_client.CreateCampaignRequest("100.00", "USD")
    )
    python_app.campaign.client.add_link(
        campaign_client.AddLinkRequest(campaign_view.campaign_id, "a", "https://ok.example/a")
    )

    rows = python_app.reports.client.links_by_verdict(
        reports_client.LinksByVerdictRequest()
    ).links
    assert [row.slug for row in rows] == ["a"]


def test_an_app_refuses_a_slice_its_component_rejects() -> None:
    with pytest.raises(errors.DomainError) as caught:
        app.PythonApp(app.AppConfig(_app_spec(campaign_storage="")))

    assert caught.value.code == "missing_coordinate"


def test_an_app_refuses_an_unsupported_backend() -> None:
    with pytest.raises(errors.DomainError) as caught:
        app.PythonApp(app.AppConfig(_app_spec(linkpolicy_storage="redis")))

    assert caught.value.code == "unknown_backend"


def test_an_app_carries_the_http_slice_its_host_reads() -> None:
    python_app = app.PythonApp(app.AppConfig(_app_spec(host="127.0.0.1", port=9091)))

    assert python_app.http.host == "127.0.0.1"
    assert python_app.http.port == 9091


def test_a_loader_reads_its_repository_once_per_load() -> None:
    fake_config_repository = FakeConfigRepository()

    app.AppLoader(fake_config_repository).load()

    assert fake_config_repository.reads == 1


def test_a_loader_returns_an_app_built_from_what_the_repository_gave_it() -> None:
    python_app = app.AppLoader(FakeConfigRepository()).load()

    assert python_app.http.port == 8080
    python_app.close()


def test_each_load_builds_its_own_app() -> None:
    fake_config_repository = FakeConfigRepository()

    first = app.AppLoader(fake_config_repository).load()
    second = app.AppLoader(fake_config_repository).load()

    assert first.campaign.client is not second.campaign.client
    first.close()
    second.close()


def test_the_env_repository_reads_the_environment_the_runner_supplied() -> None:
    app_config = app.EnvConfigRepository().get()

    assert isinstance(app_config, app.AppConfig)
    assert app_config.campaign.storage == "memory"
    assert app_config.linkpolicy.storage == "memory"


def test_each_read_returns_its_own_config() -> None:
    env_config_repository = app.EnvConfigRepository()

    assert env_config_repository.get() is not env_config_repository.get()
