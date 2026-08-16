from tesser.app.config import Config
from tesser.app.config_repository import ConfigRepository


class _Slice(Config):
    pass


class _Structural:
    def get(self) -> _Slice:
        return _Slice()


def test_a_config_repository_is_read_through_the_config_it_yields() -> None:
    reader: ConfigRepository[_Slice] = _Structural()

    assert isinstance(reader.get(), _Slice)


def test_a_structural_implementation_needs_no_marker() -> None:
    reader: ConfigRepository[_Slice] = _Structural()

    assert ConfigRepository not in type(reader).__mro__
