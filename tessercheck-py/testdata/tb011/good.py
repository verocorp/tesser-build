from dataclasses import dataclass


@dataclass(frozen=True)
class Member:
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("member must not be empty")


class Roster:
    def __init__(self, id: str, members: list[Member]) -> None:
        self._id = id
        self._members = list(members)

    @property
    def members(self) -> list[Member]:
        return list(self._members)

    def add(self, member: Member) -> None:
        self._members = [*self._members, member]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Roster) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
