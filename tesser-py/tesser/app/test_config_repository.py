from typing import Protocol

from tesser.app.config import Config
from tesser.app.config_repository import ConfigRepository


class _Reads(ConfigRepository, Protocol):
    def get(self) -> Config: ...


class _Structural:
    def get(self) -> Config:
        return Config()


def test_a_config_repository_subclass_stays_a_protocol() -> None:
    assert getattr(_Reads, "_is_protocol", False)
    assert ConfigRepository in _Reads.__mro__


def test_a_structural_implementation_needs_no_marker() -> None:
    reader: _Reads = _Structural()

    assert isinstance(reader.get(), Config)
    assert ConfigRepository not in type(reader).__mro__
