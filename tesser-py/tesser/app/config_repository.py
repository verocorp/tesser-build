from typing import Protocol, TypeVar

from tesser.app.config import Config

C_co = TypeVar("C_co", bound=Config, covariant=True)


class ConfigRepository(Protocol[C_co]):
    def get(self) -> C_co: ...
