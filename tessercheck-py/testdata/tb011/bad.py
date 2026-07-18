"""An aggregate that leaks its backing collection through an accessor — TB011.

``Roster`` is an entity (identity equality), but its ``members`` accessor hands
back ``self._members`` directly. A caller can now ``roster.members.append(x)``
and mutate the aggregate's internals without going through ``add`` — bypassing
whatever invariant the root guards. Return ``list(self._members)`` instead.
"""


class Roster:
    def __init__(self, id: str, members: list[str]) -> None:
        self._id = id
        self._members = list(members)

    @property
    def members(self) -> list[str]:
        return self._members  # leaks the backing list — TB011

    def add(self, member: str) -> None:
        self._members = [*self._members, member]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Roster) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
