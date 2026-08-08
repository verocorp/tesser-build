from tesser.domain.valueobject import ValueObject


class Truth(ValueObject):

    def __init__(self, holds: bool) -> None:
        object.__setattr__(self, "_holds", holds)

    def __bool__(self) -> bool:
        return self._holds

    _holds: bool
