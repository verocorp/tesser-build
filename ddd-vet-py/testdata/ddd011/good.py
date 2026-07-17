"""An aggregate that copies its collection out on access — DDD011 clean.

``Roster`` is an entity (identity equality by id, not by value). It owns a list
of members and its accessor returns a *copy* (``list(self._members)``), so a
caller mutating the returned list cannot reach into the aggregate's internals —
every real change goes through the root-guarded ``add`` transition.
"""


class Roster:
    def __init__(self, id: str, members: list[str]) -> None:
        self._id = id
        self._members = list(members)  # own your copy

    @property
    def members(self) -> list[str]:
        return list(self._members)  # defensive copy out

    def add(self, member: str) -> None:
        self._members = [*self._members, member]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Roster) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
