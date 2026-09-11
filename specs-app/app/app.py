from __future__ import annotations

import os
import typing

import tesser.app as ts

import specification.component as component
import tesser.errors as errors


class HttpSpec(ts.Spec):

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class HttpConfig(ts.Config):

    def __init__(self, spec: HttpSpec) -> None:
        self.host = spec.host
        self.port = spec.port


class Spec(ts.Spec):

    def __init__(self, specification: component.Config, http: HttpConfig) -> None:
        self.specification = specification
        self.http = http


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.specification = spec.specification
        self.http = spec.http


class SpecsApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.specification = component.Specification(app_config.specification)
        self.http = app_config.http

    def close(self) -> None:
        self.specification.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        storage = os.environ.get("SPECIFICATION_STORAGE")
        if storage is None:
            raise errors.invalid("missing_env", "SPECIFICATION_STORAGE is required")
        http_host = os.environ.get("HTTP_HOST")
        if http_host is None:
            raise errors.invalid("missing_env", "HTTP_HOST is required")
        raw_port = os.environ.get("HTTP_PORT")
        if raw_port is None:
            raise errors.invalid("missing_env", "HTTP_PORT is required")
        try:
            http_port = int(raw_port)
        except ValueError:
            raise errors.invalid("bad_http_port", f"HTTP_PORT must be an integer, got {raw_port!r}") from None
        return AppConfig(
            Spec(
                specification=component.Config(component.Spec(storage=storage)),
                http=HttpConfig(HttpSpec(host=http_host, port=http_port)),
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> SpecsApp:
        return SpecsApp(self._app_config_repository.get())


@ts.load
def load() -> SpecsApp:
    return AppLoader(EnvConfigRepository()).load()
