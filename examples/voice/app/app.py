from __future__ import annotations

import os
import typing

import tesser.app as ts

import calls.component as calls_component
import pgdatabase.database as pgdatabase_database
import tesser.errors as errors

_REQUIRED: typing.Final[tuple[str, ...]] = (
    "CALLS_STORAGE",
    "RESTATE_URL",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_AGENT_NAME",
)


class Spec(ts.Spec):

    def __init__(self, calls: calls_component.Config) -> None:
        self.calls = calls


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.calls = spec.calls


class VoiceApp(ts.App):

    def __init__(self, app_config: AppConfig) -> None:
        self.database = pgdatabase_database.Database(app_config.calls.database)
        self.calls = calls_component.Calls(app_config.calls, self.database)

    async def open(self) -> None:
        await self.database.open()

    async def close(self) -> None:
        await self.calls.close()
        await self.database.close()


class AppConfigRepository(ts.ConfigRepository, typing.Protocol):

    def get(self) -> AppConfig: ...


class EnvConfigRepository(AppConfigRepository):

    def get(self) -> AppConfig:
        settings: dict[str, str] = {}
        for name in _REQUIRED:
            value = os.environ.get(name)
            if value is None:
                raise errors.invalid("missing_env", f"{name} is required")
            settings[name] = value
        return AppConfig(
            Spec(
                calls=calls_component.Config(
                    calls_component.Spec(
                        storage=settings["CALLS_STORAGE"],
                        restate_url=settings["RESTATE_URL"],
                        livekit_url=settings["LIVEKIT_URL"],
                        livekit_api_key=settings["LIVEKIT_API_KEY"],
                        livekit_api_secret=settings["LIVEKIT_API_SECRET"],
                        livekit_agent_name=settings["LIVEKIT_AGENT_NAME"],
                    )
                )
            )
        )


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> VoiceApp:
        return VoiceApp(self._app_config_repository.get())


@ts.load
def load() -> VoiceApp:
    return AppLoader(EnvConfigRepository()).load()
