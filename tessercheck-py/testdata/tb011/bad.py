class Roster:
    def __init__(self, id: str, members: list[str]) -> None:
        self._id = id
        self._members = list(members)

    @property
    def members(self) -> list[str]:
        return self._members

    def add(self, member: str) -> None:
        self._members = [*self._members, member]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Roster) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
