import typing

import tesser.app.config as config
import tesser.app.config_repository as config_repository


class _Reads(config_repository.ConfigRepository, typing.Protocol):
    def get(self) -> config.Config: ...


class _Structural:
    def get(self) -> config.Config:
        return config.Config()


def test_a_config_repository_subclass_stays_a_protocol() -> None:
    assert getattr(_Reads, "_is_protocol", False)
    assert config_repository.ConfigRepository in _Reads.__mro__


def test_a_structural_implementation_needs_no_marker() -> None:
    reader: _Reads = _Structural()

    assert isinstance(reader.get(), config.Config)
    assert config_repository.ConfigRepository not in type(reader).__mro__
